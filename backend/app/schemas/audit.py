from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AuditLogEntryOut(BaseModel):
    id: str
    created_at: datetime
    categorie: str
    categorie_label: str
    titre: str
    details_ligne: str
    statut_label: str
    user_id: Optional[str] = None
    user_nom: Optional[str] = None
    user_prenom: Optional[str] = None
    user_role: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    ip: Optional[str] = None


class AuditLogListOut(BaseModel):
    total: int
    date_jour: Optional[str] = None
    entries: list[AuditLogEntryOut]


class AuditUserOption(BaseModel):
    id: str
    nom: str
    prenom: str
    role: str
