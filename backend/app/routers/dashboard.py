from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.db_errors import http_exception_from_db_error
from app.core.dependencies import require_role
from app.database import get_db
from app.models.invoice import Facture, FactureStatut
from app.models.passage_accueil import PassageAccueil
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.dashboard import (
    FactureAdminOut,
    FacturesAdminListOut,
    FacturesQuickStatsOut,
    FinanceByServiceOut,
    FinanceDailyOut,
    FinanceDashboardOut,
    FinanceSummaryOut,
    ServicePopulaireOut,
    ServiceRentabiliteOut,
    StatsReportOut,
)
from app.services.dashboard_finance import (
    PERIODE_LABELS,
    datetime_range,
    period_bounds,
    service_from_numero,
    service_label,
    statut_affichage,
    to_decimal,
)

OBJECTIF_CA_FCFA = Decimal("1500000")

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_role_admin_or_comptable = require_role(UserRole.admin.value, UserRole.comptable.value)


def _to_decimal(v: object, default: str = "0") -> Decimal:
    if isinstance(v, Decimal):
        return v
    if v is None:
        return Decimal(default)
    return Decimal(str(v))


def _service_from_numero(numero: str) -> str:
    return service_from_numero(numero)


def _top_services_consultes(db: Session, d0: date, d1: date, limit: int = 5) -> list[ServicePopulaireOut]:
    start_dt, end_dt = datetime_range(d0, d1)
    rows = db.execute(
        select(Facture.numero_facture).where(
            Facture.created_at >= start_dt,
            Facture.created_at < end_dt,
            Facture.est_annulee.is_(False),
        )
    ).all()
    counts: dict[str, int] = {}
    for (numero,) in rows:
        svc = service_from_numero(str(numero))
        counts[svc] = counts.get(svc, 0) + 1
    total = sum(counts.values()) or 1
    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [
        ServicePopulaireOut(
            service=svc,
            libelle=service_label(svc),
            nombre=n,
            pourcentage=round((n / total) * 100, 1),
        )
        for svc, n in ranked
    ]


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Format date invalide (YYYY-MM-DD)") from e


def _ca_sur_periode(db: Session, d0: date, d1: date) -> Decimal:
    start_dt = datetime.combine(d0, datetime.min.time())
    end_dt = datetime.combine(d1 + timedelta(days=1), datetime.min.time())
    rows = db.execute(
        select(Facture.montant_regle).where(
            Facture.created_at >= start_dt,
            Facture.created_at < end_dt,
            Facture.est_annulee.is_(False),
        )
    ).all()
    return sum((_to_decimal(r[0]) for r in rows), Decimal("0"))


_SERVICE_SHORT = {
    "hospitalisation": "Hospit.",
    "consultation": "Consult.",
    "pharmacie": "Pharmacie",
    "laboratoire": "Labo",
    "imagerie": "Imagerie",
    "autre": "Autre",
}


@router.get("/stats-report", response_model=StatsReportOut)
def stats_report(
    db: Session = Depends(get_db),
    _: User = Depends(_role_admin_or_comptable),
):
    """KPIs et graphiques pour Statistiques & Rapports."""
    try:
        today = date.today()
        month_start = today.replace(day=1)
        prev_month_end = month_start - timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)

        ca_mois = _ca_sur_periode(db, month_start, today)
        ca_prev = _ca_sur_periode(db, prev_month_start, prev_month_end)
        ca_var: float | None = None
        if ca_prev > 0:
            ca_var = round(float(((ca_mois - ca_prev) / ca_prev) * 100), 1)

        start_m, end_m = datetime_range(month_start, today)
        start_pm, end_pm = datetime_range(prev_month_start, prev_month_end)

        patients_mois = int(
            db.scalar(
                select(func.count())
                .select_from(PassageAccueil)
                .where(
                    PassageAccueil.created_at >= start_m,
                    PassageAccueil.created_at < end_m,
                )
            )
            or 0
        )
        patients_prev = int(
            db.scalar(
                select(func.count())
                .select_from(PassageAccueil)
                .where(
                    PassageAccueil.created_at >= start_pm,
                    PassageAccueil.created_at < end_pm,
                )
            )
            or 0
        )
        pat_var: float | None = None
        if patients_prev > 0:
            pat_var = round(((patients_mois - patients_prev) / patients_prev) * 100, 1)

        fact_rows = db.execute(
            select(Facture.montant_total, Facture.montant_regle).where(
                Facture.created_at >= start_m,
                Facture.created_at < end_m,
                Facture.est_annulee.is_(False),
            )
        ).all()
        total_mt = sum((to_decimal(r[0]) for r in fact_rows), Decimal("0"))
        total_mr = sum((to_decimal(r[1]) for r in fact_rows), Decimal("0"))
        taux_rec = float(round((total_mr / total_mt * 100) if total_mt > 0 else 0, 1))

        factures_emises = len(fact_rows)

        d7 = today - timedelta(days=6)
        ca_7: list[FinanceDailyOut] = []
        for i in range(7):
            j = d7 + timedelta(days=i)
            ca_7.append(
                FinanceDailyOut(jour=j, montant_regle=_ca_sur_periode(db, j, j))
            )

        data_fin = finance_dashboard(
            date_debut=month_start.isoformat(),
            date_fin=today.isoformat(),
            db=db,
        )  # type: ignore[arg-type]
        total_regle_services = sum(
            (to_decimal(s.montant_regle) for s in data_fin.par_service), Decimal("0")
        ) or Decimal("1")
        services_rent = []
        for s in sorted(
            data_fin.par_service,
            key=lambda x: to_decimal(x.montant_regle),
            reverse=True,
        ):
            mr = to_decimal(s.montant_regle)
            pct = float(round((mr / total_regle_services) * 100, 1))
            services_rent.append(
                ServiceRentabiliteOut(
                    service=s.service,
                    libelle=_SERVICE_SHORT.get(s.service, s.service),
                    pourcentage=pct,
                    montant_fcfa=mr,
                )
            )

        mois_label = today.strftime("%B %Y")
        return StatsReportOut(
            periode_label=mois_label,
            ca_mois=ca_mois,
            ca_mois_variation_pct=ca_var,
            patients_mois=patients_mois,
            patients_variation_pct=pat_var,
            taux_recouvrement=taux_rec,
            factures_emises=factures_emises,
            ca_7_jours=ca_7,
            services_rentabilite=services_rent,
        )
    except HTTPException:
        raise
    except (OperationalError, ProgrammingError) as e:
        raise http_exception_from_db_error(e) from e


@router.get("/summary", response_model=FinanceSummaryOut)
def finance_summary(
    db: Session = Depends(get_db),
    _: User = Depends(_role_admin_or_comptable),
):
    """Résumé du jour pour le tableau de bord admin."""
    try:
        today = date.today()
        yesterday = today - timedelta(days=1)

        ca_today = _ca_sur_periode(db, today, today)
        ca_yesterday = _ca_sur_periode(db, yesterday, yesterday)
        variation_pct: float | None = None
        if ca_yesterday > 0:
            variation_pct = float(
                round(((ca_today - ca_yesterday) / ca_yesterday) * 100, 1)
            )

        start_dt = datetime.combine(today, datetime.min.time())
        end_dt = datetime.combine(today + timedelta(days=1), datetime.min.time())

        factures_rows = db.execute(
            select(Facture.statut, Facture.montant_total, Facture.montant_regle).where(
                Facture.created_at >= start_dt,
                Facture.created_at < end_dt,
                Facture.est_annulee.is_(False),
            )
        ).all()

        payees = en_attente = impayees = 0
        for statut, mt, mr in factures_rows:
            st = statut.value if hasattr(statut, "value") else str(statut)
            if st == FactureStatut.payee.value:
                payees += 1
            elif st == FactureStatut.en_attente.value:
                en_attente += 1
            elif st in (
                FactureStatut.retard.value,
                FactureStatut.partielle.value,
            ) or (_to_decimal(mr) < _to_decimal(mt) and st != FactureStatut.payee.value):
                impayees += 1

        patients_count = int(
            db.scalar(
                select(func.count())
                .select_from(PassageAccueil)
                .where(
                    PassageAccueil.created_at >= start_dt,
                    PassageAccueil.created_at < end_dt,
                )
            )
            or 0
        )

        services_top = _top_services_consultes(
            db, today - timedelta(days=30), today, limit=5
        )

        return FinanceSummaryOut(
            date_jour=today,
            chiffre_affaires=ca_today,
            chiffre_affaires_hier=ca_yesterday,
            variation_pct=variation_pct,
            objectif_ca_fcfa=OBJECTIF_CA_FCFA,
            factures_total=len(factures_rows),
            factures_payees=payees,
            factures_en_attente=en_attente,
            factures_impayees=impayees,
            patients_enregistres=patients_count,
            services_plus_consultes=services_top,
        )
    except (OperationalError, ProgrammingError) as e:
        raise http_exception_from_db_error(e) from e


@router.get("/finance", response_model=FinanceDashboardOut)
def finance_dashboard(
    date_debut: str | None = Query(default=None, description="YYYY-MM-DD"),
    date_fin: str | None = Query(default=None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    _: User = Depends(_role_admin_or_comptable),
):
    """Dashboard financier consolidé (revenus par service)."""
    try:
        d0 = _parse_date(date_debut) or (date.today() - timedelta(days=30))
        d1 = _parse_date(date_fin) or date.today()
        if d1 < d0:
            raise HTTPException(status_code=400, detail="date_fin doit être >= date_debut")

        start_dt = datetime.combine(d0, datetime.min.time())
        end_dt = datetime.combine(d1 + timedelta(days=1), datetime.min.time())

        rows = db.execute(
            select(
                Facture.numero_facture,
                Facture.montant_total,
                Facture.montant_regle,
                Facture.created_at,
            ).where(Facture.created_at >= start_dt, Facture.created_at < end_dt)
        ).all()

        by_service: dict[str, dict[str, Decimal | int]] = {}
        by_day: dict[date, Decimal] = {}

        total_montant = Decimal("0")
        total_regle = Decimal("0")

        for numero, montant_total, montant_regle, created_at in rows:
            service = _service_from_numero(str(numero))
            mt = _to_decimal(montant_total)
            mr = _to_decimal(montant_regle)
            total_montant += mt
            total_regle += mr

            bucket = by_service.setdefault(
                service,
                {"montant_total": Decimal("0"), "montant_regle": Decimal("0"), "factures": 0},
            )
            bucket["montant_total"] = Decimal(str(bucket["montant_total"])) + mt
            bucket["montant_regle"] = Decimal(str(bucket["montant_regle"])) + mr
            bucket["factures"] = int(bucket["factures"]) + 1

            if created_at is not None:
                j = created_at.date()
                by_day[j] = by_day.get(j, Decimal("0")) + mr

        par_service = []
        for service, b in sorted(by_service.items()):
            mt = Decimal(str(b["montant_total"]))
            mr = Decimal(str(b["montant_regle"]))
            par_service.append(
                FinanceByServiceOut(
                    service=service,
                    montant_total=mt,
                    montant_regle=mr,
                    restant=max(Decimal("0"), mt - mr),
                    factures=int(b["factures"]),
                )
            )

        par_jour = [
            FinanceDailyOut(jour=j, montant_regle=by_day[j]) for j in sorted(by_day.keys())
        ]

        return FinanceDashboardOut(
            date_debut=d0,
            date_fin=d1,
            total_montant=total_montant,
            total_regle=total_regle,
            total_restant=max(Decimal("0"), total_montant - total_regle),
            par_service=par_service,
            par_jour=par_jour,
        )
    except HTTPException:
        raise
    except (OperationalError, ProgrammingError) as e:
        raise http_exception_from_db_error(e) from e


@router.get("/finance/pdf")
def finance_report_pdf(
    date_debut: str | None = Query(default=None, description="YYYY-MM-DD"),
    date_fin: str | None = Query(default=None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    _: User = Depends(_role_admin_or_comptable),
):
    """Export PDF du rapport financier (consolidé)."""
    data = finance_dashboard(date_debut=date_debut, date_fin=date_fin, db=db)  # type: ignore[arg-type]

    buf = __build_finance_pdf(data)
    filename = f"rapport_financier_{data.date_debut}_{data.date_fin}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def __build_finance_pdf(data: FinanceDashboardOut):
    from io import BytesIO

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    y = height - 40
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "Clinique Espoir — Rapport financier")
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Période: {data.date_debut} → {data.date_fin}")
    y -= 24

    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, f"Total facturé: {data.total_montant:,.0f} FCFA")
    y -= 16
    c.drawString(40, y, f"Total encaissé: {data.total_regle:,.0f} FCFA")
    y -= 16
    c.drawString(40, y, f"Total restant: {data.total_restant:,.0f} FCFA")
    y -= 22

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Détail par service")
    y -= 14
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "Service")
    c.drawRightString(300, y, "Factures")
    c.drawRightString(390, y, "Facturé")
    c.drawRightString(470, y, "Encaissé")
    c.drawRightString(540, y, "Restant")
    y -= 10
    c.line(40, y, width - 40, y)
    y -= 16
    c.setFont("Helvetica", 10)

    for s in data.par_service:
        c.drawString(40, y, s.service)
        c.drawRightString(300, y, str(s.factures))
        c.drawRightString(390, y, f"{s.montant_total:,.0f}")
        c.drawRightString(470, y, f"{s.montant_regle:,.0f}")
        c.drawRightString(540, y, f"{s.restant:,.0f}")
        y -= 14
        if y < 80:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 10)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


def _compute_factures_stats(rows: list[tuple]) -> FacturesQuickStatsOut:
    total_facture = Decimal("0")
    payees_count = en_attente_count = impayees_count = 0
    payees_montant = en_attente_montant = impayees_montant = Decimal("0")

    for _num, mt, mr, statut in rows:
        montant = to_decimal(mt)
        regle = to_decimal(mr)
        total_facture += montant
        code, _ = statut_affichage(statut, montant, regle)
        if code == "payee":
            payees_count += 1
            payees_montant += montant
        elif code == "en_attente":
            en_attente_count += 1
            en_attente_montant += montant - regle if montant > regle else montant
        else:
            impayees_count += 1
            impayees_montant += max(Decimal("0"), montant - regle)

    return FacturesQuickStatsOut(
        total_facture=total_facture,
        payees_count=payees_count,
        payees_montant=payees_montant,
        en_attente_count=en_attente_count,
        en_attente_montant=en_attente_montant,
        impayees_count=impayees_count,
        impayees_montant=impayees_montant,
    )


@router.get("/factures", response_model=FacturesAdminListOut)
def list_factures_admin(
    date_debut: str | None = Query(default=None),
    date_fin: str | None = Query(default=None),
    statut: str | None = Query(default=None, description="payee|en_attente|partielle|impayee"),
    service: str | None = Query(default=None),
    recherche: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(_role_admin_or_comptable),
):
    """Liste des factures pour la gestion admin."""
    try:
        d0 = _parse_date(date_debut) or (date.today() - timedelta(days=30))
        d1 = _parse_date(date_fin) or date.today()
        if d1 < d0:
            raise HTTPException(status_code=400, detail="date_fin doit être >= date_debut")

        start_dt, end_dt = datetime_range(d0, d1)
        stmt = (
            select(
                Facture,
                Patient.nom,
                Patient.prenom,
            )
            .join(Patient, Patient.id == Facture.patient_id)
            .where(
                Facture.created_at >= start_dt,
                Facture.created_at < end_dt,
                Facture.est_annulee.is_(False),
            )
            .order_by(Facture.created_at.desc())
            .limit(limit)
        )
        rows = db.execute(stmt).all()

        factures_out: list[FactureAdminOut] = []
        stats_rows: list[tuple] = []

        for facture, nom, prenom in rows:
            svc = service_from_numero(facture.numero_facture)
            if service and service != "tous" and svc != service:
                continue
            mt = to_decimal(facture.montant_total)
            mr = to_decimal(facture.montant_regle)
            code, label = statut_affichage(facture.statut, mt, mr)
            if statut and statut != "tous" and code != statut:
                continue
            q = (recherche or "").strip().lower()
            if q:
                blob = f"{facture.numero_facture} {nom} {prenom}".lower()
                if q not in blob:
                    continue

            stats_rows.append((facture.numero_facture, mt, mr, facture.statut))
            factures_out.append(
                FactureAdminOut(
                    id=facture.id,
                    numero_facture=facture.numero_facture,
                    patient_nom=nom,
                    patient_prenom=prenom,
                    service=svc,
                    service_label=service_label(svc),
                    montant_total=mt,
                    montant_regle=mr,
                    statut=code,
                    statut_label=label,
                    date_emission=facture.created_at.date(),
                )
            )

        return FacturesAdminListOut(
            total=len(factures_out),
            factures=factures_out,
            stats=_compute_factures_stats(stats_rows),
        )
    except HTTPException:
        raise
    except (OperationalError, ProgrammingError) as e:
        raise http_exception_from_db_error(e) from e


@router.get("/reports/pdf")
def report_pdf(
    periode: str = Query(..., description="journalier|hebdomadaire|mensuel|trimestriel"),
    date_ref: str | None = Query(default=None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    _: User = Depends(_role_admin_or_comptable),
):
    ref = _parse_date(date_ref) or date.today()
    d0, d1 = period_bounds(periode, ref)
    data = finance_dashboard(date_debut=d0.isoformat(), date_fin=d1.isoformat(), db=db)  # type: ignore[arg-type]
    buf = __build_finance_pdf(data)
    label = PERIODE_LABELS.get(periode.lower(), periode)
    filename = f"rapport_{label.lower()}_{d0}_{d1}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports/excel")
def report_excel(
    periode: str = Query(...),
    date_ref: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(_role_admin_or_comptable),
):
    from io import BytesIO, StringIO
    import csv

    ref = _parse_date(date_ref) or date.today()
    d0, d1 = period_bounds(periode, ref)
    start_dt, end_dt = datetime_range(d0, d1)

    rows = db.execute(
        select(
            Facture.numero_facture,
            Patient.nom,
            Patient.prenom,
            Facture.montant_total,
            Facture.montant_regle,
            Facture.statut,
            Facture.created_at,
        )
        .join(Patient, Patient.id == Facture.patient_id)
        .where(
            Facture.created_at >= start_dt,
            Facture.created_at < end_dt,
            Facture.est_annulee.is_(False),
        )
        .order_by(Facture.created_at.desc())
    ).all()

    sio = StringIO()
    writer = csv.writer(sio, delimiter=";")
    writer.writerow(
        [
            "N° Facture",
            "Patient",
            "Service",
            "Montant total",
            "Montant réglé",
            "Statut",
            "Date",
        ]
    )
    for numero, nom, prenom, mt, mr, st, created in rows:
        svc = service_label(service_from_numero(str(numero)))
        code, label = statut_affichage(st, to_decimal(mt), to_decimal(mr))
        writer.writerow(
            [
                numero,
                f"{prenom} {nom}",
                svc,
                f"{to_decimal(mt):,.0f}",
                f"{to_decimal(mr):,.0f}",
                label,
                created.date().isoformat() if created else "",
            ]
        )

    label = PERIODE_LABELS.get(periode.lower(), periode)
    buf = BytesIO()
    buf.write("\ufeff".encode("utf-8"))
    buf.write(sio.getvalue().encode("utf-8"))
    buf.seek(0)
    filename = f"rapport_{label.lower()}_{d0}_{d1}.csv"
    return StreamingResponse(
        buf,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
