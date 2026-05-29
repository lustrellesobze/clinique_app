from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.db_errors import http_exception_from_db_error
from app.core.dependencies import require_role
from app.database import get_db
from app.models.audit import AuditLog
from app.models.user import User, UserRole
from app.schemas.audit import AuditLogEntryOut, AuditLogListOut, AuditUserOption
from app.services.audit_display import build_entry

router = APIRouter(prefix="/audit", tags=["audit"])

_role_admin = require_role(UserRole.admin.value)


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Format date invalide (YYYY-MM-DD)") from e


@router.get("/users", response_model=list[AuditUserOption])
def list_audit_users(
    db: Session = Depends(get_db),
    _: User = Depends(_role_admin),
):
    users = db.scalars(
        select(User).where(User.est_actif.is_(True)).order_by(User.nom, User.prenom)
    ).all()
    return [
        AuditUserOption(
            id=u.id,
            nom=u.nom,
            prenom=u.prenom,
            role=u.role.value if hasattr(u.role, "value") else str(u.role),
        )
        for u in users
    ]


@router.get("", response_model=AuditLogListOut)
def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    user_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    categorie: str | None = Query(default=None, description="FACTURE|PAIEMENT|PATIENT|..."),
    recherche: str | None = Query(default=None),
    date_debut: str | None = Query(default=None, description="YYYY-MM-DD"),
    date_fin: str | None = Query(default=None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    _: User = Depends(_role_admin),
):
    try:
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if action and action != "toutes":
            stmt = stmt.where(AuditLog.action == action)

        d0 = _parse_date(date_debut)
        d1 = _parse_date(date_fin)
        if not d0 and not d1:
            d1 = date.today()
            d0 = d1
        elif d0 and not d1:
            d1 = d0
        elif d1 and not d0:
            d0 = d1

        if d0 and d1:
            start_dt = datetime.combine(d0, datetime.min.time())
            end_dt = datetime.combine(d1 + timedelta(days=1), datetime.min.time())
            stmt = stmt.where(
                AuditLog.created_at >= start_dt,
                AuditLog.created_at < end_dt,
            )

        if recherche and recherche.strip():
            q = f"%{recherche.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    AuditLog.action.ilike(q),
                    AuditLog.entity_type.ilike(q),
                    AuditLog.entity_id.ilike(q),
                    AuditLog.details_json.ilike(q),
                )
            )

        rows = db.scalars(stmt.limit(limit * 3)).all()

        user_ids = {r.user_id for r in rows if r.user_id}
        users_map: dict[str, User] = {}
        if user_ids:
            users = db.scalars(select(User).where(User.id.in_(user_ids))).all()
            users_map = {u.id: u for u in users}

        entries: list[AuditLogEntryOut] = []
        for r in rows:
            built = build_entry(r, users_map.get(r.user_id) if r.user_id else None)
            if categorie and categorie != "toutes" and built["categorie"] != categorie.upper():
                continue
            entries.append(
                AuditLogEntryOut(
                    id=built["id"],
                    created_at=built["created_at"],
                    categorie=built["categorie"],
                    categorie_label=built["categorie_label"],
                    titre=built["titre"],
                    details_ligne=built["details_ligne"],
                    statut_label=built["statut_label"],
                    user_id=built["user_id"],
                    user_nom=built["user_nom"],
                    user_prenom=built["user_prenom"],
                    user_role=built["user_role"],
                    action=built["action"],
                    entity_type=built["entity_type"],
                    entity_id=built["entity_id"],
                    ip=built["ip"],
                )
            )
            if len(entries) >= limit:
                break

        date_jour = d0.isoformat() if d0 else None
        return AuditLogListOut(
            total=len(entries),
            date_jour=date_jour,
            entries=entries,
        )
    except HTTPException:
        raise
    except (OperationalError, ProgrammingError) as e:
        raise http_exception_from_db_error(e) from e
