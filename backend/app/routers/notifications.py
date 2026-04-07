"""
Routes API pour la gestion des notifications
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.services.notification_service import NotificationService


router = APIRouter(prefix="/notifications", tags=["notifications"])


# Schémas Pydantic
class NotificationResponse(BaseModel):
    id: str
    user_id: str
    type_notification: str
    titre: str
    message: str
    est_lue: bool
    created_at: str
    
    class Config:
        from_attributes = True


class NotificationCreate(BaseModel):
    user_id: str
    type_notification: str
    titre: str
    message: str


class UnreadCountResponse(BaseModel):
    count: int


@router.get("/", response_model=List[NotificationResponse])
def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère les notifications de l'utilisateur connecté"""
    notifications = NotificationService.get_user_notifications(
        db=db,
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit
    )
    
    return [
        NotificationResponse(
            id=n.id,
            user_id=n.user_id,
            type_notification=n.type_notification,
            titre=n.titre,
            message=n.message,
            est_lue=n.est_lue,
            created_at=n.created_at.isoformat()
        )
        for n in notifications
    ]


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Compte les notifications non lues"""
    count = NotificationService.get_unread_count(db=db, user_id=current_user.id)
    return UnreadCountResponse(count=count)


@router.put("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Marque une notification comme lue"""
    notification = NotificationService.mark_as_read(db=db, notification_id=notification_id)
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification non trouvée"
        )
    
    # Vérifier que la notification appartient à l'utilisateur
    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )
    
    return NotificationResponse(
        id=notification.id,
        user_id=notification.user_id,
        type_notification=notification.type_notification,
        titre=notification.titre,
        message=notification.message,
        est_lue=notification.est_lue,
        created_at=notification.created_at.isoformat()
    )


@router.put("/mark-all-read")
def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Marque toutes les notifications comme lues"""
    count = NotificationService.mark_all_as_read(db=db, user_id=current_user.id)
    return {"message": f"{count} notification(s) marquée(s) comme lue(s)"}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprime une notification"""
    # Vérifier que la notification appartient à l'utilisateur
    notification = db.get(Notification, notification_id)
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification non trouvée"
        )
    
    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )
    
    success = NotificationService.delete_notification(db=db, notification_id=notification_id)
    
    if success:
        return {"message": "Notification supprimée"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la suppression"
        )


@router.post("/", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
def create_notification(
    notification_data: NotificationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crée une nouvelle notification (admin uniquement)"""
    # TODO: Ajouter vérification du rôle admin
    
    notification = NotificationService.create_notification(
        db=db,
        user_id=notification_data.user_id,
        type_notification=notification_data.type_notification,
        titre=notification_data.titre,
        message=notification_data.message
    )
    
    return NotificationResponse(
        id=notification.id,
        user_id=notification.user_id,
        type_notification=notification.type_notification,
        titre=notification.titre,
        message=notification.message,
        est_lue=notification.est_lue,
        created_at=notification.created_at.isoformat()
    )
