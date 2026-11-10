import os

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError
from .database import get_db
from .models import User
from .auth import decode_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login-docs")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception=HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Could not validate credentials",headers={"WWW-Authenticate":"Bearer"})
    try:
        payload=decode_token(token)
        username=payload.get("sub")
        if not username: raise credentials_exception
    except JWTError:
        raise credentials_exception
    user=db.query(User).filter(User.username==username).first()
    if not user: raise credentials_exception
    if user.status!="Approved":
        raise HTTPException(status_code=403,detail=f"Account not active. Status: {user.status}")
    return user

def require_role(allowed_roles: list[str]):
    def checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403,detail="Operation not permitted for current user role")
        return current_user
    return checker

    
def require_main_admin():
    def checker(current_user: User = Depends(get_current_user)):
        main_admin_username = os.getenv(
            "DEFAULT_ADMIN_USERNAME", "admin"
        ).strip().lower()

        if (
            current_user.username != main_admin_username
            or current_user.role != "Administrator"
        ):
            raise HTTPException(
                status_code=403,
                detail="Main Administrator permission required"
            )

        return current_user

    return checker

