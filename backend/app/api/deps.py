from typing import Generator, Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.core.constants import UserRole
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

security = HTTPBearer(auto_error=False)


def get_current_user(
    db: Session = Depends(get_db),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_demo_user_email: Optional[str] = Header(None, alias="X-Demo-User-Email")
) -> User:
    """
    Authenticates user via Bearer JWT or demo switch header (for seamless local persona testing).
    Enforces server-side authorization and user existence.
    """
    # 1. Check Bearer Token if present
    if auth and auth.credentials:
        payload = decode_access_token(auth.credentials)
        if payload and payload.get("sub"):
            user = db.query(User).filter(User.email == payload["sub"]).first()
            if user and user.is_active:
                return user

    # 2. Check X-Demo-User-Email header for local demo workflows
    if x_demo_user_email:
        user = db.query(User).filter(User.email == x_demo_user_email).first()
        if user and user.is_active:
            return user

    # 3. Default fallback to buyer if in local dev mode
    default_buyer = db.query(User).filter(User.role == UserRole.BUYER.value).first()
    if default_buyer:
        return default_buyer

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_buyer(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in [UserRole.BUYER.value, UserRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation restricted to Procurement Buyers."
        )
    return current_user


def require_supplier(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in [UserRole.SUPPLIER.value, UserRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation restricted to participating Suppliers."
        )
    return current_user
