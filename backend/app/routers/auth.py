import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.db_errors import http_exception_from_db_error
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token_payload,
    verify_password,
)
from app.database import get_db
from app.models.user import User
from app.schemas.auth import RefreshRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _token_payload_for_user(user: User) -> dict:
    return {
        "sub": user.id,
        "role": user.role.value,
        "email": user.email,
    }


def _build_token_response(user: User) -> dict:
    payload = _token_payload_for_user(user)
    access = create_access_token(payload.copy())
    refresh = create_refresh_token({"sub": user.id})
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "nom": user.nom,
            "prenom": user.prenom,
            "email": user.email,
            "role": user.role.value,
            "service": user.service,
        },
    }


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    try:
        stmt = select(User).where(
            User.email == form_data.username,
            User.est_actif.is_(True),
        )
        user = db.scalars(stmt).first()
    except (OperationalError, ProgrammingError) as e:
        raise http_exception_from_db_error(e) from e

    if not user or not verify_password(form_data.password, user.mot_de_passe_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    try:
        return _build_token_response(user)
    except Exception:
        logger.exception("Erreur inattendue pendant la génération JWT (voir cause ci-dessous)")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Échec lors de la création du jeton. Consultez le terminal Uvicorn. "
                "Vérifiez : pip install -r requirements.txt, redémarrage du serveur, "
                "SECRET_KEY présent dans backend/.env."
            ),
        ) from None


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(
    body: RefreshRequest,
    db: Session = Depends(get_db),
):
    try:
        payload = decode_refresh_token_payload(body.refresh_token)
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError()
        user_id = str(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide ou expiré",
        )

    try:
        stmt = select(User).where(User.id == user_id, User.est_actif.is_(True))
        user = db.scalars(stmt).first()
    except (OperationalError, ProgrammingError) as e:
        raise http_exception_from_db_error(e) from e

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable",
        )

    return _build_token_response(user)
