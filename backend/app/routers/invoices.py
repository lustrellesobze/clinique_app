import secrets
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session, selectinload

from app.core.db_errors import http_exception_from_db_error
from app.core.dependencies import require_role
from app.database import get_db
from app.models.invoice import Facture, FactureStatut, LigneFacture
from app.models.patient import Patient
from app.models.payment import Paiement
from app.models.user import User, UserRole
from app.schemas.caisse import (
    CreateConsultationInvoiceIn,
    InvoiceLineOut,
    InvoiceOut,
    PatientCaisseOut,
    PaymentOut,
)
from app.services.consultation_info_service import (
    creer_facture_consultation_depuis_passage,
    get_consultation_info,
    get_dernier_passage_actif,
    get_facture_consultation_en_attente,
    get_facture_consultation_pour_caisse,
)
from app.services.pdf_service import PDFService

router = APIRouter(prefix="/invoices", tags=["invoices"])

_role_caisse_or_admin = require_role(
    UserRole.caissier_central.value,
    UserRole.admin.value,
)


def _to_decimal(v: object, default: str = "0") -> Decimal:
    if isinstance(v, Decimal):
        return v
    if v is None:
        return Decimal(default)
    return Decimal(str(v))


def _patient_to_out(p: Patient, db: Session) -> PatientCaisseOut:
    info = get_consultation_info(db, p)
    return PatientCaisseOut(
        id=p.id,
        code_patient=p.code_patient,
        nom=p.nom,
        prenom=p.prenom,
        date_naissance=p.date_naissance,
        telephone=p.telephone,
        email=p.email,
        medecin_id=p.medecin_id,
        assureur=p.assureur,
        numero_police_assurance=p.numero_police_assurance,
        est_actif=p.est_actif,
        medecin_nom=info.get("medecin_nom"),
        batiment=info.get("batiment"),
        type_consultation_label=info.get("type_consultation_label"),
        motif_consultation=info.get("motif_consultation") or None,
        montant_consultation_fcfa=info.get("montant_consultation_fcfa"),
        remise_passage_fcfa=info.get("remise_passage_fcfa"),
    )


def _payment_to_out(p: Paiement) -> PaymentOut:
    return PaymentOut(
        id=p.id,
        facture_id=p.facture_id,
        caissier_id=p.caissier_id,
        montant=_to_decimal(p.montant),
        mode_paiement=(
            p.mode_paiement.value
            if hasattr(p.mode_paiement, "value")
            else str(p.mode_paiement)
        ),
        statut=p.statut.value if hasattr(p.statut, "value") else str(p.statut),
        reference_transaction=p.reference_transaction,
        commentaire=p.commentaire,
        created_at=p.created_at,
    )


def _load_paiements_map(db: Session, facture_ids: list[str]) -> dict[str, list[Paiement]]:
    if not facture_ids:
        return {}
    rows = db.scalars(
        select(Paiement)
        .where(Paiement.facture_id.in_(facture_ids))
        .order_by(Paiement.created_at.asc())
    ).all()
    out: dict[str, list[Paiement]] = {}
    for p in rows:
        out.setdefault(p.facture_id, []).append(p)
    return out


def _invoice_to_out(
    inv: Facture,
    patient: Patient | None = None,
    db: Session | None = None,
    paiements: list[Paiement] | None = None,
) -> InvoiceOut:
    total = _to_decimal(inv.montant_total)
    regle = _to_decimal(inv.montant_regle)
    lines = [
        InvoiceLineOut(
            id=l.id,
            ordre=l.ordre,
            designation=l.designation,
            quantite=_to_decimal(l.quantite),
            prix_unitaire=_to_decimal(l.prix_unitaire),
            remise_montant=_to_decimal(l.remise_montant),
            montant_ligne=_to_decimal(l.montant_ligne),
        )
        for l in inv.lignes
    ]
    info: dict = {}
    if patient and db is not None:
        info = get_consultation_info(db, patient)
    return InvoiceOut(
        id=inv.id,
        numero_facture=inv.numero_facture,
        patient_id=inv.patient_id,
        caissier_id=inv.caissier_id,
        statut=inv.statut.value if hasattr(inv.statut, "value") else str(inv.statut),
        montant_total=total,
        montant_regle=regle,
        restant_a_payer=max(Decimal("0"), total - regle),
        remise_globale=_to_decimal(inv.remise_globale),
        part_assurance=_to_decimal(inv.part_assurance)
        if inv.part_assurance is not None
        else None,
        part_patient=_to_decimal(inv.part_patient) if inv.part_patient is not None else None,
        devise=inv.devise,
        commentaire=inv.commentaire,
        created_at=inv.created_at,
        lignes=lines,
        patient=_patient_to_out(patient, db) if patient and db is not None else None,
        medecin_nom=info.get("medecin_nom"),
        batiment=info.get("batiment"),
        type_consultation_label=info.get("type_consultation_label"),
        code_patient=patient.code_patient if patient else None,
        paiements=[_payment_to_out(p) for p in (paiements or [])],
    )


def _generer_numero_facture(db: Session) -> str:
    year = datetime.now().year
    for _ in range(100):
        suffix = f"{secrets.randbelow(100000):05d}"
        num = f"FACT-CONS-{year}-{suffix}"
        exists = db.scalar(select(Facture.id).where(Facture.numero_facture == num))
        if not exists:
            return num
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Impossible de générer un numéro de facture unique",
    )


@router.post("", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_consultation_invoice(
    body: CreateConsultationInvoiceIn,
    db: Session = Depends(get_db),
    current: User = Depends(_role_caisse_or_admin),
):
    try:
        patient: Patient | None = None
        if body.patient_id:
            patient = db.scalars(
                select(Patient).where(
                    Patient.id == body.patient_id,
                    Patient.est_actif.is_(True),
                )
            ).first()
        elif body.code_patient:
            patient = db.scalars(
                select(Patient).where(
                    Patient.code_patient == body.code_patient,
                    Patient.est_actif.is_(True),
                )
            ).first()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fournir patient_id ou code_patient",
            )
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient introuvable",
            )

        # Par défaut : facture déjà créée à l'accueil ou générée depuis le passage.
        lines_in = body.lignes
        if not lines_in:
            passage = get_dernier_passage_actif(db, patient.id)
            if not passage:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Aucun passage d'accueil trouvé pour ce patient. "
                        "Renseignez des lignes manuelles."
                    ),
                )
            inv_existing = creer_facture_consultation_depuis_passage(
                db,
                patient,
                passage,
                caissier_id=current.id,
                commentaire=body.commentaire,
            )
            db.commit()
            inv = db.scalars(
                select(Facture)
                .where(Facture.id == inv_existing.id)
                .options(selectinload(Facture.lignes))
            ).first()
            assert inv is not None
            pay_map = _load_paiements_map(db, [inv.id])
            return _invoice_to_out(inv, patient, db, pay_map.get(inv.id, []))

        existing_pending = get_facture_consultation_en_attente(db, patient.id)
        if existing_pending:
            inv = db.scalars(
                select(Facture)
                .where(Facture.id == existing_pending.id)
                .options(selectinload(Facture.lignes))
            ).first()
            assert inv is not None
            pay_map = _load_paiements_map(db, [inv.id])
            return _invoice_to_out(inv, patient, db, pay_map.get(inv.id, []))

        facture = Facture(
            numero_facture=_generer_numero_facture(db),
            patient_id=patient.id,
            caissier_id=current.id,
            statut=FactureStatut.en_attente,
            devise="XAF",
            commentaire=body.commentaire,
            remise_globale=float(_to_decimal(body.remise_globale)),
        )
        db.add(facture)
        db.flush()

        total = Decimal("0")
        for idx, line in enumerate(lines_in, start=1):
            designation = (
                line.designation if hasattr(line, "designation") else line["designation"]
            )
            quantite = _to_decimal(
                line.quantite if hasattr(line, "quantite") else line["quantite"], "1"
            )
            prix = _to_decimal(
                line.prix_unitaire
                if hasattr(line, "prix_unitaire")
                else line["prix_unitaire"]
            )
            remise = _to_decimal(
                line.remise_montant
                if hasattr(line, "remise_montant")
                else line["remise_montant"]
            )
            montant_ligne = max(Decimal("0"), quantite * prix - remise)
            total += montant_ligne

            db.add(
                LigneFacture(
                    facture_id=facture.id,
                    ordre=idx,
                    designation=designation,
                    quantite=float(quantite),
                    prix_unitaire=float(prix),
                    remise_montant=float(remise),
                    montant_ligne=float(montant_ligne),
                )
            )

        total = max(Decimal("0"), total - _to_decimal(body.remise_globale))
        facture.montant_total = float(total)
        facture.part_patient = float(total)
        facture.montant_regle = 0
        facture.statut = FactureStatut.en_attente if total > 0 else FactureStatut.payee
        info = get_consultation_info(db, patient)
        if info.get("medecin_nom"):
            note = (
                f"Consultation — {info['medecin_nom']} — {info.get('batiment') or ''}"
            )
            facture.commentaire = (
                f"{body.commentaire.strip()} | {note}"
                if body.commentaire
                else note
            )
        db.commit()

        inv = db.scalars(
            select(Facture)
            .where(Facture.id == facture.id)
            .options(selectinload(Facture.lignes))
        ).first()
        assert inv is not None
        pay_map = _load_paiements_map(db, [inv.id])
        return _invoice_to_out(inv, patient, db, pay_map.get(inv.id, []))
    except HTTPException:
        db.rollback()
        raise
    except (OperationalError, ProgrammingError) as e:
        db.rollback()
        raise http_exception_from_db_error(e) from e


@router.get("/consultation-active", response_model=InvoiceOut)
def get_consultation_active_invoice(
    patient_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    _: User = Depends(_role_caisse_or_admin),
):
    """Facture consultation unique pour la caisse (en attente prioritaire)."""
    try:
        inv = get_facture_consultation_pour_caisse(db, patient_id)
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucune facture de consultation pour ce patient",
            )
        inv = db.scalars(
            select(Facture)
            .where(Facture.id == inv.id)
            .options(selectinload(Facture.lignes))
        ).first()
        if not inv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facture introuvable")
        patient = db.get(Patient, patient_id)
        pay_map = _load_paiements_map(db, [inv.id])
        return _invoice_to_out(inv, patient, db, pay_map.get(inv.id, []))
    except HTTPException:
        raise
    except (OperationalError, ProgrammingError) as e:
        raise http_exception_from_db_error(e) from e


@router.get("", response_model=list[InvoiceOut])
def list_invoices(
    patient_id: str | None = Query(default=None),
    code_patient: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(_role_caisse_or_admin),
):
    try:
        stmt = select(Facture).options(selectinload(Facture.lignes)).order_by(
            Facture.created_at.desc()
        )

        patient_map: dict[str, Patient] = {}
        if patient_id:
            stmt = stmt.where(Facture.patient_id == patient_id)
        elif code_patient:
            p = db.scalars(select(Patient).where(Patient.code_patient == code_patient)).first()
            if not p:
                return []
            stmt = stmt.where(Facture.patient_id == p.id)
            patient_map[p.id] = p

        rows = db.scalars(stmt.limit(50)).all()
        if not patient_map:
            patient_ids = {r.patient_id for r in rows}
            if patient_ids:
                pats = db.scalars(select(Patient).where(Patient.id.in_(patient_ids))).all()
                patient_map = {p.id: p for p in pats}
        pay_map = _load_paiements_map(db, [i.id for i in rows])
        return [
            _invoice_to_out(
                i,
                patient_map.get(i.patient_id),
                db,
                pay_map.get(i.id, []),
            )
            for i in rows
        ]
    except (OperationalError, ProgrammingError) as e:
        raise http_exception_from_db_error(e) from e


@router.get("/{invoice_id}/pdf")
def export_invoice_pdf(
    invoice_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(_role_caisse_or_admin),
):
    try:
        inv = db.scalars(
            select(Facture)
            .where(Facture.id == invoice_id)
            .options(selectinload(Facture.lignes))
        ).first()
        if not inv:
            raise HTTPException(status_code=404, detail="Facture introuvable")
        patient = db.scalars(select(Patient).where(Patient.id == inv.patient_id)).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient introuvable")

        info = get_consultation_info(db, patient)
        paiements = db.scalars(
            select(Paiement)
            .where(Paiement.facture_id == inv.id)
            .order_by(Paiement.created_at.asc())
        ).all()

        insurance = None
        if patient.assureur:
            from app.models.insurance import Insurance

            insurance = db.scalars(
                select(Insurance).where(Insurance.nom_compagnie == patient.assureur)
            ).first()

        caissier_nom = None
        if inv.caissier_id:
            caissier = db.scalars(
                select(User).where(User.id == inv.caissier_id)
            ).first()
            if caissier:
                caissier_nom = f"{caissier.prenom} {caissier.nom}".strip()

        buf = PDFService.generate_invoice_pdf(
            inv,
            patient,
            insurance,
            consultation_info=info,
            paiements=list(paiements),
            caissier_nom=caissier_nom,
        )
        filename = f"{inv.numero_facture}.pdf"
        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except (OperationalError, ProgrammingError) as e:
        raise http_exception_from_db_error(e) from e
