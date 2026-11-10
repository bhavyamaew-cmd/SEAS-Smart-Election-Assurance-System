from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_main_admin
from ..models import User, Booth, BoothStaffAssignment


router = APIRouter(
    prefix="/api/admin/assignments",
    tags=["Booth Staff Assignments"],
)


class AutoAssignRequest(BaseModel):
    election_cycle: str = Field(
        ...,
        min_length=1,
        max_length=30,
        pattern=r"^[A-Za-z0-9_-]+$",
    )


@router.get("/status")
def assignment_status(
    db: Session = Depends(get_db),
    admin=Depends(require_main_admin()),
):
    return {
        "message": "Booth assignment API is ready",
        "admin": admin.username,
    }


@router.get("/list")
def list_assignments(
    election_cycle: str,
    db: Session = Depends(get_db),
    admin=Depends(require_main_admin()),
):
    assignments = (
        db.query(BoothStaffAssignment)
        .filter(
            BoothStaffAssignment.election_cycle == election_cycle,
            BoothStaffAssignment.status == "Active",
        )
        .order_by(
            BoothStaffAssignment.booth_id,
            BoothStaffAssignment.role,
        )
        .all()
    )

    results = []

    for assignment in assignments:
        booth = db.query(Booth).filter(
            Booth.id == assignment.booth_id
        ).first()

        staff = db.query(User).filter(
            User.id == assignment.user_id
        ).first()

        print(
            "DEBUG ASSIGNMENT:",
            assignment.id,
            assignment.booth_id,
            assignment.user_id,
            staff.username if staff else "USER NOT FOUND"
        )
        
        if not staff:
            staff = db.query(User).filter(
                User.username == str(assignment.user_id)
            ).first()

        results.append({
            "assignment_id": assignment.id,
            "booth_id": assignment.booth_id,
            "booth_name": booth.name if booth else None,
            "booth_number": booth.booth_number if booth else None,
            "staff_id": assignment.user_id,
            "staff_name": staff.username if staff else None,
            "username": staff.username if staff else None,
            "role": assignment.role,
            "election_cycle": assignment.election_cycle,
            "assigned_by": assignment.assigned_by,
            "status": assignment.status,
        })

    return {
        "election_cycle": election_cycle,
        "total_assignments": len(results),
        "assignments": results,
    }



class EditAssignmentRequest(BaseModel):
    staff_id: int


@router.put("/{assignment_id}")
def edit_assignment(
    assignment_id: int,
    payload: EditAssignmentRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_main_admin()),
):
    assignment = (
        db.query(BoothStaffAssignment)
        .filter(
            BoothStaffAssignment.id == assignment_id,
            BoothStaffAssignment.status == "Active",
        )
        .first()
    )

    if not assignment:
        raise HTTPException(
            status_code=404,
            detail="Active booth assignment not found.",
        )

    staff = (
        db.query(User)
        .filter(
            User.id == payload.staff_id,
            User.status == "Approved",
            User.role == assignment.role,
        )
        .first()
    )

    if not staff:
        raise HTTPException(
            status_code=400,
            detail="Select an approved staff member with the same role.",
        )

    duplicate = (
        db.query(BoothStaffAssignment)
        .filter(
            BoothStaffAssignment.user_id == staff.id,
            BoothStaffAssignment.election_cycle == assignment.election_cycle,
            BoothStaffAssignment.status == "Active",
            BoothStaffAssignment.id != assignment.id,
        )
        .first()
    )

    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="This staff member is already assigned in this election cycle.",
        )

    previous_staff_id = assignment.user_id

    assignment.user_id = staff.id
    assignment.assigned_by = admin.username

    try:
        db.commit()
        db.refresh(assignment)
    except Exception:
        db.rollback()
        raise

    return {
        "message": "Booth assignment updated successfully.",
        "assignment_id": assignment.id,
        "booth_id": assignment.booth_id,
        "previous_staff_id": previous_staff_id,
        "staff_id": assignment.user_id,
        "role": assignment.role,
        "election_cycle": assignment.election_cycle,
    }



@router.post("/auto-assign")
def auto_assign(
    payload: AutoAssignRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_main_admin()),
):
    cycle = payload.election_cycle.strip()

    booths = (
        db.query(Booth)
        .filter(Booth.status == "Active")
        .order_by(Booth.id)
        .all()
    )

    if not booths:
        raise HTTPException(
            status_code=400,
            detail="No active polling booths were found.",
        )

    required_roles = [
        "Booth Administrator",
        "Verifier",
        "Officer",
    ]

    existing = (
        db.query(BoothStaffAssignment)
        .filter(
            BoothStaffAssignment.election_cycle == cycle,
            BoothStaffAssignment.status == "Active",
        )
        .order_by(BoothStaffAssignment.id)
        .all()
    )

    existing_pairs = {
        (assignment.booth_id, assignment.role)
        for assignment in existing
    }

    assigned_user_ids = {
        assignment.user_id
        for assignment in existing
    }

    staff_by_role = {}

    for role in required_roles:
        staff_by_role[role] = (
            db.query(User)
            .filter(
                User.role == role,
                User.status == "Approved",
            )
            .order_by(User.id)
            .all()
        )

    missing_by_role = {}

    for role in required_roles:
        missing_count = sum(
            1
            for booth in booths
            if (booth.id, role) not in existing_pairs
        )

        available_count = sum(
            1
            for user in staff_by_role[role]
            if user.id not in assigned_user_ids
        )

        if available_count < missing_count:
            missing_by_role[role] = {
                "required": missing_count,
                "available": available_count,
                "shortage": missing_count - available_count,
            }

    if missing_by_role:
        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    "Insufficient approved staff. "
                    "No new assignments were created."
                ),
                "election_cycle": cycle,
                "staff_shortages": missing_by_role,
            },
        )

    new_assignments = []

    try:
        for role in required_roles:
            available_staff = [
                user
                for user in staff_by_role[role]
                if user.id not in assigned_user_ids
            ]

            for booth in booths:
                if (booth.id, role) in existing_pairs:
                    continue

                user = available_staff.pop(0)

                new_assignments.append(
                    BoothStaffAssignment(
                        booth_id=booth.id,
                        user_id=user.id,
                        role=role,
                        election_cycle=cycle,
                        assigned_by=admin.username,
                        status="Active",
                    )
                )

                assigned_user_ids.add(user.id)
                existing_pairs.add((booth.id, role))

        db.add_all(new_assignments)
        db.commit()

    except Exception:
        db.rollback()
        raise

    return {
        "message": "Automatic booth assignment completed.",
        "election_cycle": cycle,
        "active_booths": len(booths),
        "new_assignments": len(new_assignments),
        "preserved_assignments": len(existing),
    }
