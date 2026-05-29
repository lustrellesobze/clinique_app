import base64
import io
import re
import secrets
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session
import qrcode

from app.core.db_errors import http_exception_from_db_error
from app.core.dependencies import require_role
from app.core.realtime import caisse_realtime_manager
from app.config import settings
from app.database import get_db
from app.models.invoice import Facture, FactureStatut
from app.models.payment import ModePaiement, Paiement, StatutPaiement
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.caisse import (
    MobilePaymentInitIn,
    MobilePaymentInitOut,
    PaymentCreateIn,
    PaymentOut,
    PaymentStatusOut,
)
from app.services.audit_service import log_audit
from app.services.campay_service import (
    CampayError,
    campay_is_enabled,
    create_payment_link,
    get_transaction_status,
    initiate_collection,
    normalize_cameroon_phone,
)
from app.services.campay_webhook import (
    apply_campay_notification_to_payment,
    finalize_confirmed_mobile_payment_effects,
    parse_campay_transaction_notification,
)
from app.services.email_service import try_send_email
from app.services.loyalty_service import LoyaltyService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/payments", tags=["payments"])

_role_caisse_or_admin = require_role(
    UserRole.caissier_central.value,
    UserRole.admin.value,
)


_CAMPAY_LINK_REF_RE = re.compile(r"campay_link_ref=([^\s|]+)")


def _campay_link_ref_from_comment(commentaire: str | None) -> str | None:
    if not commentaire:
        return None
    m = _CAMPAY_LINK_REF_RE.search(commentaire)
    return m.group(1) if m else None


def _qr_png_base64(payload: str) -> tuple[str, str]:
    img = qrcode.make(payload)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii"), payload


def _to_decimal(v: object, default: str = "0") -> Decimal:
    if isinstance(v, Decimal):
        return v
    if v is None:
        return Decimal(default)
    return Decimal(str(v))


def _build_payment_status(payment: Paiement, facture: Facture) -> PaymentStatusOut:
    total = _to_decimal(facture.montant_total)
    regle = _to_decimal(facture.montant_regle)
    return PaymentStatusOut(
        payment_id=payment.id,
        statut=payment.statut.value,
        facture_statut=facture.statut.value,
        montant_regle=regle,
        restant_a_payer=max(Decimal("0"), total - regle),
    )


@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(
    body: PaymentCreateIn,
    db: Session = Depends(get_db),
    current: User = Depends(_role_caisse_or_admin),
):
    try:
        facture = db.scalars(select(Facture).where(Facture.id == body.facture_id)).first()
        if not facture:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Facture introuvable",
            )

        total = _to_decimal(facture.montant_total)
        regle = _to_decimal(facture.montant_regle)
        montant = _to_decimal(body.montant)
        restant = max(Decimal("0"), total - regle)
        if montant > restant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Montant trop élevé. Reste à payer: {restant} FCFA",
            )

        payment = Paiement(
            facture_id=facture.id,
            caissier_id=current.id,
            montant=float(montant),
            mode_paiement=ModePaiement(body.mode_paiement),
            statut=StatutPaiement.confirme,
            reference_transaction=body.reference_transaction,
            commentaire=body.commentaire,
        )
        db.add(payment)

        # Audit
        log_audit(
            db,
            user_id=current.id,
            action="payment_create",
            entity_type="facture",
            entity_id=facture.id,
            details={"mode": body.mode_paiement, "montant": float(montant)},
        )

        new_regle = regle + montant
        facture.montant_regle = float(new_regle)
        if new_regle >= total:
            facture.statut = FactureStatut.payee
        elif new_regle > 0:
            facture.statut = FactureStatut.partielle
        else:
            facture.statut = FactureStatut.en_attente

        db.commit()
        db.refresh(payment)

        # Fidélité + notification patient (best effort)
        try:
            patient = db.scalars(select(Patient).where(Patient.id == facture.patient_id)).first()
            if patient:
                earned = LoyaltyService.add_points_for_payment(db, patient.id, montant)
                db.commit()
                if patient.email:
                    sent = try_send_email(
                        to_email=patient.email,
                        subject="Reçu de paiement — Clinique",
                        body=(
                            f"Bonjour {patient.prenom} {patient.nom},\n\n"
                            f"Nous confirmons la réception de votre paiement de {float(montant):,.0f} FCFA.\n"
                            f"Référence: {body.reference_transaction or '-'}\n"
                            f"Facture: {facture.numero_facture}\n\n"
                            f"Points fidélité gagnés: {earned}\n"
                            f"Merci.\n"
                        ),
                    )
                    log_audit(
                        db,
                        user_id=current.id,
                        action="patient_email_payment_receipt",
                        entity_type="patient",
                        entity_id=patient.id,
                        details={"sent": sent, "email": patient.email},
                    )
                    db.commit()

                # Notification interne au caissier (websocket)
                NotificationService.create_notification(
                    db=db,
                    user_id=current.id,
                    type_notification="paiement",
                    titre="Paiement enregistré",
                    message=(
                        f"Paiement {float(montant):,.0f} FCFA. Points gagnés: {earned}. "
                        f"Patient: {patient.nom} {patient.prenom}"
                        if patient
                        else f"Paiement {float(montant):,.0f} FCFA."
                    ),
                )
        except Exception:
            pass

        return payment
    except HTTPException:
        db.rollback()
        raise
    except (OperationalError, ProgrammingError) as e:
        db.rollback()
        raise http_exception_from_db_error(e) from e


@router.post(
    "/mobile/initiate",
    response_model=MobilePaymentInitOut,
    status_code=status.HTTP_201_CREATED,
)
def initiate_mobile_payment(
    body: MobilePaymentInitIn,
    db: Session = Depends(get_db),
    current: User = Depends(_role_caisse_or_admin),
):
    """Initie un paiement mobile (Campay si configuré, sinon mode mock)."""
    try:
        facture = db.scalars(select(Facture).where(Facture.id == body.facture_id)).first()
        if not facture:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Facture introuvable",
            )
        total = _to_decimal(facture.montant_total)
        regle = _to_decimal(facture.montant_regle)
        montant = _to_decimal(body.montant)
        restant = max(Decimal("0"), total - regle)
        if montant > restant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Montant trop élevé. Reste à payer: {restant} FCFA",
            )

        ref = body.reference_transaction or (
            f"{'OM' if body.provider == 'orange_money' else 'MM'}"
            f"-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.randbelow(1000):03d}"
        )
        commentaire = "Paiement mobile initié (mode démo — Campay non configuré)."
        payment_link_url: str | None = None
        campay_link_ref: str | None = None

        patient = db.get(Patient, facture.patient_id)
        raw_phone = (body.telephone or "").strip() or (
            (patient.telephone or "").strip() if patient else ""
        )

        if campay_is_enabled():
            if not raw_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Numéro Mobile Money requis (saisir le téléphone du patient "
                        "ou renseigner le téléphone à l'accueil)."
                    ),
                )
            try:
                phone = normalize_cameroon_phone(raw_phone)
                label = "Orange Money" if body.provider == "orange_money" else "MTN MoMo"
                desc = f"Paiement facture {facture.numero_facture}"
                campay_result = initiate_collection(
                    amount=montant,
                    phone_number=phone,
                    provider=body.provider,
                    external_reference=ref,
                    description=desc,
                )
                ref = campay_result.reference or ref
                try:
                    link_result = create_payment_link(
                        amount=montant,
                        phone_number=phone,
                        external_reference=ref,
                        description=desc,
                        first_name=(patient.prenom if patient else "") or "Client",
                        last_name=(patient.nom if patient else "") or "Clinique",
                        email=(patient.email if patient else "") or "",
                        payment_options="MOMO",
                    )
                    payment_link_url = link_result.link
                    campay_link_ref = link_result.reference
                except CampayError:
                    pass
                commentaire = (
                    f"Paiement {label} initié via Campay sur {phone}. "
                    f"Statut collect: {campay_result.status}."
                )
                if campay_link_ref:
                    commentaire += f" campay_link_ref={campay_link_ref}"
                if payment_link_url:
                    commentaire += " QR: lien Campay actif."
            except CampayError as e:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Erreur Campay: {str(e)}",
                ) from e
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Erreur technique Campay: {e}",
                ) from e

        campay_used = campay_is_enabled() and bool(raw_phone)
        phone_normalized: str | None = None
        if campay_used:
            phone_normalized = normalize_cameroon_phone(raw_phone)

        payment = Paiement(
            facture_id=facture.id,
            caissier_id=current.id,
            montant=float(montant),
            mode_paiement=ModePaiement(body.provider),
            statut=StatutPaiement.en_attente,
            reference_transaction=ref,
            commentaire=commentaire,
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        qr_b64 = ""
        qr_payload = ""
        if campay_used and payment_link_url:
            qr_b64, qr_payload = _qr_png_base64(payment_link_url)
        elif not campay_used:
            payload = (
                f"CLINIQUE|facture={facture.numero_facture}|montant={montant}|"
                f"provider={body.provider}|ref={ref}"
            )
            qr_b64, qr_payload = _qr_png_base64(payload)

        label = "Orange Money" if body.provider == "orange_money" else "MTN MoMo"
        if campay_used:
            instructions = [
                f"Demande {label} envoyée au {phone_normalized} (notification sur le téléphone).",
            ]
            if payment_link_url:
                instructions.extend(
                    [
                        "Si le client ne reçoit pas la notification à temps, scannez le QR code "
                        "affiché à la caisse (page de paiement Campay).",
                        "Ne validez qu'une seule fois : notification OU QR, pas les deux.",
                    ]
                )
            else:
                instructions.append(
                    "Validez le paiement sur le téléphone du client, puis « Vérifier statut »."
                )
            instructions.append(
                "Après paiement, cliquez sur « Vérifier statut » pour mettre à jour la facture."
            )
        else:
            instructions = [
                "Mode démo (Campay non actif) : utilisez « Confirmer (test) » pour simuler.",
            ]

        return MobilePaymentInitOut(
            payment=payment,
            qr_png_base64=qr_b64,
            qr_payload=qr_payload,
            instructions=instructions,
            campay_active=campay_used,
            telephone=phone_normalized,
            payment_link=payment_link_url,
        )
    except HTTPException:
        db.rollback()
        raise
    except (OperationalError, ProgrammingError) as e:
        db.rollback()
        raise http_exception_from_db_error(e) from e


@router.get("/mobile/{payment_id}/status", response_model=PaymentStatusOut)
def mobile_payment_status(
    payment_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(_role_caisse_or_admin),
):
    try:
        payment = db.scalars(select(Paiement).where(Paiement.id == payment_id)).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Paiement introuvable")
        facture = db.scalars(select(Facture).where(Facture.id == payment.facture_id)).first()
        if not facture:
            raise HTTPException(status_code=404, detail="Facture introuvable")

        if (
            payment.statut == StatutPaiement.en_attente
            and payment.reference_transaction
            and campay_is_enabled()
        ):
            refs: list[str] = []
            for r in (
                payment.reference_transaction,
                _campay_link_ref_from_comment(payment.commentaire),
            ):
                if r and r not in refs:
                    refs.append(r)
            outcome = "noop"
            for campay_ref in refs:
                try:
                    tx = get_transaction_status(campay_ref)
                    notify = parse_campay_transaction_notification(tx)
                    outcome = apply_campay_notification_to_payment(
                        db,
                        payment=payment,
                        facture=facture,
                        notify=notify,
                        append_comment=False,
                    )
                    if outcome == "confirmed":
                        finalize_confirmed_mobile_payment_effects(db, payment, facture)
                        break
                    if outcome == "failed":
                        break
                except CampayError:
                    continue
            if outcome != "noop":
                db.commit()
                db.refresh(payment)
                db.refresh(facture)
                import asyncio

                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(
                        caisse_realtime_manager.broadcast(
                            {
                                "event": "mobile_payment_updated",
                                "payment_id": payment.id,
                                "reference_transaction": payment.reference_transaction,
                                "payment_status": payment.statut.value,
                                "invoice_id": facture.id,
                                "invoice_status": facture.statut.value,
                                "invoice_paid": float(facture.montant_regle or 0),
                                "campay_sync": outcome,
                            }
                        )
                    )
                except RuntimeError:
                    pass

        return _build_payment_status(payment, facture)
    except HTTPException:
        raise
    except (OperationalError, ProgrammingError) as e:
        raise http_exception_from_db_error(e) from e


@router.post("/mobile/{payment_id}/confirm", response_model=PaymentStatusOut)
def confirm_mobile_payment_mock(
    payment_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(_role_caisse_or_admin),
):
    """Confirmation mock manuelle (en attendant webhook opérateur)."""
    try:
        payment = db.scalars(select(Paiement).where(Paiement.id == payment_id)).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Paiement introuvable")
        facture = db.scalars(select(Facture).where(Facture.id == payment.facture_id)).first()
        if not facture:
            raise HTTPException(status_code=404, detail="Facture introuvable")

        if payment.statut == StatutPaiement.en_attente:
            payment.statut = StatutPaiement.confirme
            total = _to_decimal(facture.montant_total)
            regle = _to_decimal(facture.montant_regle) + _to_decimal(payment.montant)
            facture.montant_regle = float(regle)
            if regle >= total:
                facture.statut = FactureStatut.payee
            elif regle > 0:
                facture.statut = FactureStatut.partielle
            else:
                facture.statut = FactureStatut.en_attente
            db.commit()
            db.refresh(payment)
            db.refresh(facture)

            # Audit + fidélité + notification interne
            try:
                log_audit(
                    db,
                    user_id=payment.caissier_id,
                    action="mobile_payment_confirm",
                    entity_type="paiement",
                    entity_id=payment.id,
                    details={"facture_id": facture.id, "montant": float(payment.montant)},
                )
                patient = db.scalars(select(Patient).where(Patient.id == facture.patient_id)).first()
                if patient:
                    LoyaltyService.add_points_for_payment(db, patient.id, _to_decimal(payment.montant))
                db.commit()
            except Exception:
                pass
            import asyncio

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    caisse_realtime_manager.broadcast(
                        {
                            "event": "mobile_payment_updated",
                            "payment_id": payment.id,
                            "reference_transaction": payment.reference_transaction,
                            "payment_status": payment.statut.value,
                            "invoice_id": facture.id,
                            "invoice_status": facture.statut.value,
                            "invoice_paid": float(facture.montant_regle or 0),
                        }
                    )
                )
            except RuntimeError:
                pass

        return _build_payment_status(payment, facture)
    except HTTPException:
        db.rollback()
        raise
    except (OperationalError, ProgrammingError) as e:
        db.rollback()
        raise http_exception_from_db_error(e) from e


@router.get("", response_model=list[PaymentOut])
def list_payments(
    facture_id: str = Query(min_length=1),
    db: Session = Depends(get_db),
    _: User = Depends(_role_caisse_or_admin),
):
    try:
        rows = db.scalars(
            select(Paiement)
            .where(Paiement.facture_id == facture_id)
            .order_by(Paiement.created_at.desc())
        ).all()
        return rows
    except (OperationalError, ProgrammingError) as e:
        raise http_exception_from_db_error(e) from e
