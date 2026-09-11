from pydantic import BaseModel

from app.models.enums import UserRole


class LoginRequest(BaseModel):
    # Plain str, not EmailStr: our own seed accounts use the RFC 2606 `.test` TLD
    # (editor@peblo.test / admin@peblo.test), which email-validator rejects as a
    # reserved/special-use domain. A malformed email just fails the DB lookup -> 401.
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    role: UserRole

    model_config = {"from_attributes": True}
