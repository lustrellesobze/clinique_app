"""Vérification des rôles — à compléter."""
from typing import List
from fastapi import Depends, HTTPException, status
from app.core.dependencies import get_current_user
from app.models.user import User, UserRole


def require_role(allowed_roles: List[UserRole]):
    """
    Dépendance FastAPI pour vérifier que l'utilisateur a l'un des rôles autorisés
    
    Usage:
        @router.get("/endpoint")
        def my_endpoint(
            current_user: User = Depends(require_role([UserRole.admin, UserRole.comptable]))
        ):
            ...
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès refusé. Rôles autorisés: {[role.value for role in allowed_roles]}"
            )
        return current_user
    
    return role_checker

