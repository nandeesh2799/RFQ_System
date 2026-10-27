from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.core.constants import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    company_name: str
    role: UserRole = UserRole.SUPPLIER
    supplier_code: str | None = None


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class TokenPayload(BaseModel):
    sub: str | None = None
    role: str | None = None
    user_id: int | None = None
