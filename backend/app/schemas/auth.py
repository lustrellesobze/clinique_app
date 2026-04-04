from typing import Optional

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    nom: str
    prenom: str
    email: str
    role: str
    service: Optional[str] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse
