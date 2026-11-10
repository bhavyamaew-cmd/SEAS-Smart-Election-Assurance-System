from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import (
    Voter,
    User,
    AuditLog,
    BoothStaffAssignment,
    VoteTally,
    ElectionResultArchive,
)
from ..schemas import VoterResponse, VoterCreate, VoterUpdate
from ..dependencies import get_current_user, require_role


router=APIRouter(prefix="/api/voters",tags=["Voter Management"])

def log_action(db,user,action,ip=None):
    db.add(AuditLog(user_id=user.id,username=user.username,action=action,ip_address=ip));db.commit()

@router.get("",response_model=list[VoterResponse])
def list_voters(db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    return db.query(Voter).order_by(Voter.created_at.desc()).all()

@router.get("/{voter_id}",response_model=VoterResponse)
def get_voter(voter_id:str,db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    voter=db.query(Voter).filter(Voter.id.ilike(voter_id)).first()
    if not voter: raise HTTPException(status_code=404,detail="Voter not found")
    return voter


from pydantic import BaseModel

class VoterStatusUpdate(BaseModel):
    status: str


@router.patch("/{voter_id}/verification-status")
def update_verification_status(
    voter_id: str,
    payload: VoterStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    voter = db.query(Voter).filter(
        Voter.id.ilike(voter_id)
    ).first()

    if not voter:
        raise HTTPException(status_code=404, detail="Voter not found")
        
    print("DEBUG STATUS:", repr(payload.status))

    if payload.status not in ["Verified", "Voted"]:
        raise HTTPException(status_code=400, detail="Invalid voter status")

    if payload.status == "Voted" and voter.status != "Verified":
        raise HTTPException(
            status_code=409,
            detail="Voter must be verified before being marked as voted"
        )

    voter.status = payload.status
    db.commit()
    db.refresh(voter)

    log_action(
        db,
        current_user,
        f"Voter status updated to {voter.status}: {voter.id}",
        request.client.host if request.client else None
    )

    return {"voter_id": voter.id, "status": voter.status}

@router.post("",response_model=VoterResponse,status_code=201)
def create_voter(payload:VoterCreate,request:Request,db:Session=Depends(get_db),current_user:User=Depends(require_role(["Administrator","Officer"]))):
    if db.query(Voter).filter(Voter.id.ilike(payload.id)).first(): raise HTTPException(status_code=409,detail="Voter ID already registered")
    if payload.fingerprint_id is not None and db.query(Voter).filter(Voter.fingerprint_id==payload.fingerprint_id).first(): raise HTTPException(status_code=409,detail=f"Fingerprint ID FP-{payload.fingerprint_id} already in use")
    voter=Voter(**payload.model_dump());db.add(voter);db.commit();db.refresh(voter)
    log_action(db,current_user,f"Voter created: {voter.id} ({voter.name})",request.client.host if request.client else None);return voter

@router.put("/{voter_id}",response_model=VoterResponse)
def update_voter(voter_id:str,payload:VoterUpdate,request:Request,db:Session=Depends(get_db),current_user:User=Depends(require_role(["Administrator","Officer"]))):
    voter=db.query(Voter).filter(Voter.id.ilike(voter_id)).first()
    if not voter: raise HTTPException(status_code=404,detail="Voter record not found")
    data=payload.model_dump(exclude_unset=True)
    new_id=data.pop("id",None)
    if new_id and new_id.lower()!=voter.id.lower():
        if db.query(Voter).filter(Voter.id.ilike(new_id)).first(): raise HTTPException(status_code=409,detail="New Voter ID already exists")
        voter.id=new_id
    if "fingerprint_id" in data and data["fingerprint_id"] is not None:
        dup=db.query(Voter).filter(Voter.fingerprint_id==data["fingerprint_id"],Voter.id!=voter.id).first()
        if dup: raise HTTPException(status_code=409,detail="Fingerprint ID already assigned to another voter")
    for key,value in data.items(): setattr(voter,key,value)
    db.commit();db.refresh(voter);log_action(db,current_user,f"Voter updated: {voter.id}",request.client.host if request.client else None);return voter


@router.delete("/{voter_id}")
def delete_voter(voter_id:str,request:Request,db:Session=Depends(get_db),current_user:User=Depends(require_role(["Administrator","Officer"]))):
    voter=db.query(Voter).filter(Voter.id.ilike(voter_id)).first()
    if not voter: raise HTTPException(status_code=404,detail="Voter not found")
    db.delete(voter);db.commit();log_action(db,current_user,f"Voter deleted: {voter_id}",request.client.host if request.client else None)
    return {"message":f"Voter {voter_id} deleted successfully"}



@router.post("/reset-election/{election_cycle}")
def reset_election(
    election_cycle: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Administrator"]))
):
    try:
        # 1. Reset voter statuses, preserving voter records and fingerprints
        voters = db.query(Voter).filter(
            Voter.status.in_(["Verified", "Voted"])
        ).all()

        for voter in voters:
            voter.status = "Pending"

        # 2. Reset each party's vote count to zero, preserving tally records
        tallies = db.query(VoteTally).all()

        for tally in tallies:
            tally.vote_count = 0

        # 3. Deactivate active booth staff assignments without deleting them
        assignments = db.query(BoothStaffAssignment).filter(
            BoothStaffAssignment.status == "Active"
        ).all()

        for assignment in assignments:
            assignment.status = "Inactive"

        # 4. Record the reset in the audit log
        db.add(AuditLog(
            user_id=current_user.id,
            username=current_user.username,
            action=(
                f"Election test reset: {len(voters)} voter statuses reset, "
                f"{len(tallies)} tally records set to zero, "
                f"{len(assignments)} booth assignments deactivated"
            ),
            ip_address=request.client.host if request.client else None
        ))

        # Commit all changes together
        db.commit()

        return {
            "message": "Election test reset completed successfully",
            "voters_reset": len(voters),
            "tally_records_reset": len(tallies),
            "booth_assignments_deactivated": len(assignments)
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Election reset failed; database changes were rolled back"
        )

