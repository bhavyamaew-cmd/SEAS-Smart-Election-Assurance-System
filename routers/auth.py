from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, AuditLog
from ..schemas import UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse
from ..auth import get_password_hash, verify_password, create_access_token
from ..dependencies import get_current_user

router=APIRouter(prefix="/api/auth",tags=["Authentication"])

def log_audit(db, action, user=None, username=None, ip=None):
    db.add(AuditLog(user_id=user.id if user else None, username=user.username if user else (username or "System"), action=action, ip_address=ip))
    db.commit()
@router.post("/register",status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterRequest, request: Request, db: Session=Depends(get_db)):
    username=payload.username.strip().lower()
    if db.query(User).filter(User.username==username).first():
        raise HTTPException(status_code=409,detail="Username already exists")
    user=User(full_name=payload.name.strip(),username=username,password_hash=get_password_hash(payload.password),role=payload.role,status="Pending")
    db.add(user);db.commit();db.refresh(user)
    log_audit(db,f"New user registered (Pending Approval): {username}",username=username,ip=request.client.host if request.client else None)
    return {"message":"Account created. Awaiting admin approval.","username":username}

@router.post("/login",response_model=TokenResponse)
def login(payload: UserLoginRequest, request: Request, db: Session=Depends(get_db)):
    username=payload.username.strip().lower()
    user=db.query(User).filter(User.username==username).first()
    if not user or not verify_password(payload.password,user.password_hash):
        log_audit(db,f"Failed login attempt for username: {username}",username=username,ip=request.client.host if request.client else None)
        raise HTTPException(status_code=401,detail="Invalid username or password")
    if user.status=="Pending": raise HTTPException(status_code=403,detail="Account is pending administrator approval")
    if user.status=="Rejected": raise HTTPException(status_code=403,detail="Account registration has been rejected")
    if user.status!="Approved": raise HTTPException(status_code=403,detail="Account is inactive")
    token=create_access_token({"sub":user.username,"role":user.role,"id":user.id})
    log_audit(db,f"User logged in successfully: {user.username}",user=user,ip=request.client.host if request.client else None)
    return {"access_token":token,"token_type":"bearer","user":user}

@router.get("/me",response_model=UserResponse)
def me(current_user: User=Depends(get_current_user)):
    return current_user

@router.post("/login-docs",include_in_schema=False)
def login_docs(form_data: OAuth2PasswordRequestForm=Depends(),request: Request=None,db: Session=Depends(get_db)):
    result=login(UserLoginRequest(username=form_data.username,password=form_data.password),request,db)
    return {"access_token":result["access_token"],"token_type":"bearer"}
