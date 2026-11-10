from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, AuditLog,BoothStaffAssignment
from ..schemas import UserResponse
from ..dependencies import require_main_admin

router=APIRouter(prefix="/api/admin/users",tags=["Administrator Management"])

def log_admin(db,admin,action,ip=None):
    db.add(AuditLog(user_id=admin.id,username=admin.username,action=action,ip_address=ip));db.commit()

@router.get("/pending",response_model=list[UserResponse])
def pending(db:Session=Depends(get_db),admin=Depends(require_main_admin())):
    return db.query(User).filter(User.status=="Pending").order_by(User.created_at.desc()).all()

@router.get("/approved",response_model=list[UserResponse])
def approved(db:Session=Depends(get_db),admin=Depends(require_main_admin())):
    return db.query(User).filter(User.status=="Approved").order_by(User.created_at.desc()).all()

@router.get("/rejected",response_model=list[UserResponse])
def rejected(db:Session=Depends(get_db),admin=Depends(require_main_admin())):
    return db.query(User).filter(User.status=="Rejected").order_by(User.created_at.desc()).all()

@router.post("/{user_id}/approve",response_model=UserResponse)
def approve(user_id:int,request:Request,db:Session=Depends(get_db),admin=Depends(require_main_admin())):
    target=db.query(User).filter(User.id==user_id).first()
    if not target: raise HTTPException(status_code=404,detail="User not found")
    if target.username=="admin": raise HTTPException(status_code=400,detail="Primary administrator is already approved")
    target.status="Approved";target.approved_by=admin.username;target.approved_at=datetime.utcnow();target.rejected_by=None;target.rejected_at=None
    db.commit();db.refresh(target);log_admin(db,admin,f"User approved: {target.username} (Role: {target.role})",request.client.host if request.client else None)
    return target

@router.post("/{user_id}/reject",response_model=UserResponse)
def reject(user_id:int,request:Request,db:Session=Depends(get_db),admin=Depends(require_main_admin())):
    target=db.query(User).filter(User.id==user_id).first()
    if not target: raise HTTPException(status_code=404,detail="User not found")
    if target.username=="admin": raise HTTPException(status_code=400,detail="Cannot reject primary administrator")
    target.status="Rejected";target.rejected_by=admin.username;target.rejected_at=datetime.utcnow();target.approved_by=None;target.approved_at=None
    db.commit();db.refresh(target);log_admin(db,admin,f"User rejected: {target.username}",request.client.host if request.client else None)
    return target


@router.delete("/{user_id}")
def delete(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_main_admin())
):
    target = db.query(User).filter(User.id == user_id).first()

    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.username == "admin":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete default system administrator"
        )

    username = target.username

    try:
        # Remove this user's booth assignments first
        db.query(BoothStaffAssignment).filter(
            BoothStaffAssignment.user_id == user_id
        ).delete(synchronize_session=False)

        # Then delete the user account
        db.delete(target)
        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not delete user and booth assignments"
        )

    log_admin(
        db,
        admin,
        f"User account permanently deleted: {username}",
        request.client.host if request.client else None
    )

    return {"message": f"User {username} and their booth assignments deleted successfully"}

