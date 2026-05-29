import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.db_errors import http_exception_from_db_error
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token_payload,
    verify_password,
)
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import (
    GoogleAuthConfigOut,
    GoogleLoginRequest,
    RefreshRequest,
    TokenResponse,
)
from app.services.google_auth_service import (
    GoogleAuthError,
    google_accueil_auth_enabled,
    verify_google_id_token,
)
from app.config import settings

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


@router.get("/google/config", response_model=GoogleAuthConfigOut)
def google_auth_config():
    """Indique si le bouton Google est actif (accueil uniquement)."""
    client_id = (settings.GOOGLE_CLIENT_ID or "").strip()
    return GoogleAuthConfigOut(
        enabled=google_accueil_auth_enabled(),
        client_id=client_id if google_accueil_auth_enabled() else "",
    )


@router.post("/google", response_model=TokenResponse)
def login_with_google(
    body: GoogleLoginRequest,
    db: Session = Depends(get_db),
):
    """
    Connexion via Google — uniquement pour les comptes ``infirmiere_accueil``.
    L'e-mail Google doit correspondre à l'e-mail du compte en base.
    """
    if not google_accueil_auth_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Connexion Google non activée.",
        )

    try:
        google_info = verify_google_id_token(body.credential)
    except GoogleAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e

    email = google_info["email"]
    try:
        user = db.scalars(
            select(User).where(
                User.email == email,
                User.est_actif.is_(True),
            )
        ).first()
    except SQLAlchemyError as e:
        raise http_exception_from_db_error(e) from e

    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Aucun compte clinique associé à ce compte Google. "
                "Demandez à l'administrateur d'enregistrer votre adresse Gmail."
            ),
        )

    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role != UserRole.infirmiere_accueil.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La connexion Google est réservée au personnel d'accueil.",
        )

    try:
        return _build_token_response(user)
    except Exception as e:
        logger.exception("Erreur JWT après connexion Google")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Échec lors de la création du jeton ({e!s}).",
        ) from e


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
    except SQLAlchemyError as e:
        raise http_exception_from_db_error(e) from e

    if not user or not verify_password(form_data.password, user.mot_de_passe_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    try:
        return _build_token_response(user)
    except Exception as e:
        logger.exception("Erreur inattendue pendant la génération JWT (voir cause ci-dessous)")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Échec lors de la création du jeton ({e!s}). Vérifiez SECRET_KEY dans "
                "backend/.env et le terminal Uvicorn pour la pile complète."
            ),
        ) from e


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
    except SQLAlchemyError as e:
        raise http_exception_from_db_error(e) from e

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable",
        )

    return _build_token_response(user)
