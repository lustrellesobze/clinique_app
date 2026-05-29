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
    refresh_token: str
    token_type: str
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str


class GoogleAuthConfigOut(BaseModel):
    enabled: bool
    client_id: str = ""


class GoogleLoginRequest(BaseModel):
    credential: str
