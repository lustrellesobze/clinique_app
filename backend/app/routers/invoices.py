import secrets
from io import BytesIO
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session, selectinload

from app.core.db_errors import http_exception_from_db_error
from app.core.dependencies import require_role
from app.database import get_db
from app.models.invoice import Facture, FactureStatut, LigneFacture
from app.models.passage_accueil import PassageAccueil
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.caisse import (
    CreateConsultationInvoiceIn,
    InvoiceLineOut,
    InvoiceOut,
    PatientCaisseOut,
)

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


def _patient_to_out(p: Patient) -> PatientCaisseOut:
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
    )


def _invoice_to_out(inv: Facture, patient: Patient | None = None) -> InvoiceOut:
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
        patient=_patient_to_out(patient) if patient else None,
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

        # Par défaut, on reprend la consultation saisie à l'accueil.
        lines_in = body.lignes
        if not lines_in:
            passage = db.scalars(
                select(PassageAccueil)
                .where(PassageAccueil.patient_id == patient.id)
                .order_by(PassageAccueil.created_at.desc())
                .limit(1)
            ).first()
            if not passage:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Aucun passage d'accueil trouvé pour ce patient. "
                        "Renseignez des lignes manuelles."
                    ),
                )
            lines_in = [
                {
                    "designation": "Consultation",
                    "quantite": Decimal("1"),
                    "prix_unitaire": _to_decimal(passage.montant_consultation_fcfa),
                    "remise_montant": _to_decimal(passage.remise_fcfa),
                }
            ]

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
        db.commit()

        inv = db.scalars(
            select(Facture)
            .where(Facture.id == facture.id)
            .options(selectinload(Facture.lignes))
        ).first()
        assert inv is not None
        return _invoice_to_out(inv, patient)
    except HTTPException:
        db.rollback()
        raise
    except (OperationalError, ProgrammingError) as e:
        db.rollback()
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
        return [_invoice_to_out(i, patient_map.get(i.patient_id)) for i in rows]
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

        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        width, height = A4
        y = height - 40
        c.setFont("Helvetica-Bold", 16)
        c.drawString(40, y, "Clinique Espoir — Facture")
        y -= 26
        c.setFont("Helvetica", 10)
        c.drawString(40, y, f"Numero: {inv.numero_facture}")
        y -= 16
        c.drawString(
            40,
            y,
            f"Patient: {(patient.nom + ' ' + patient.prenom) if patient else inv.patient_id}",
        )
        y -= 16
        c.drawString(
            40,
            y,
            f"Date: {inv.created_at.strftime('%d/%m/%Y %H:%M') if inv.created_at else '-'}",
        )
        y -= 24

        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, "Ligne")
        c.drawString(260, y, "Qte")
        c.drawString(320, y, "PU")
        c.drawString(390, y, "Remise")
        c.drawString(470, y, "Total")
        y -= 12
        c.line(40, y, width - 40, y)
        y -= 16
        c.setFont("Helvetica", 10)
        for line in inv.lignes:
            c.drawString(40, y, line.designation[:34])
            c.drawRightString(300, y, f"{_to_decimal(line.quantite)}")
            c.drawRightString(370, y, f"{_to_decimal(line.prix_unitaire)}")
            c.drawRightString(450, y, f"{_to_decimal(line.remise_montant)}")
            c.drawRightString(540, y, f"{_to_decimal(line.montant_ligne)}")
            y -= 16
            if y < 120:
                c.showPage()
                y = height - 50

        y -= 8
        c.line(360, y, width - 40, y)
        y -= 18
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(540, y, f"Sous-total: {_to_decimal(inv.montant_total) + _to_decimal(inv.remise_globale)} FCFA")
        y -= 16
        c.drawRightString(540, y, f"Remise: {_to_decimal(inv.remise_globale)} FCFA")
        y -= 16
        c.drawRightString(540, y, f"Total: {_to_decimal(inv.montant_total)} FCFA")
        y -= 16
        c.drawRightString(540, y, f"Regle: {_to_decimal(inv.montant_regle)} FCFA")
        y -= 16
        c.drawRightString(
            540,
            y,
            f"Reste: {max(Decimal('0'), _to_decimal(inv.montant_total) - _to_decimal(inv.montant_regle))} FCFA",
        )
        c.showPage()
        c.save()
        buf.seek(0)
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
