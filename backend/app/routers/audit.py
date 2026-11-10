from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import AuditLog, User
from ..schemas import AuditLogResponse, AuditLogCreate
from ..dependencies import get_current_user

router=APIRouter(prefix="/api/audit",tags=["Audit Log"])

@router.get("",response_model=list[AuditLogResponse])
def get_logs(limit:int=150,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    limit=max(1,min(limit,500))
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()

@router.post("",response_model=AuditLogResponse)
def create_log(payload:AuditLogCreate,request:Request,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    entry=AuditLog(user_id=current_user.id,username=current_user.username,action=payload.action,ip_address=request.client.host if request.client else None)
    db.add(entry);db.commit();db.refresh(entry);return entry
