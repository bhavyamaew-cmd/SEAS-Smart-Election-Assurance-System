
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import State, District, Constituency, Area, Booth

router = APIRouter(prefix="/api/locations", tags=["Locations"])


@router.get("/states")
def get_states(db: Session = Depends(get_db)):
    return db.query(State).order_by(State.name).all()


@router.get("/districts")
def get_districts(
    state_id: int = Query(...),
    db: Session = Depends(get_db)
):
    state = db.query(State).filter(State.id == state_id).first()
    if not state:
        raise HTTPException(status_code=404, detail="State not found")

    return (
        db.query(District)
        .filter(District.state_id == state_id)
        .order_by(District.name)
        .all()
    )


@router.get("/constituencies")
def get_constituencies(
    district_id: int = Query(...),
    db: Session = Depends(get_db)
):
    district = db.query(District).filter(District.id == district_id).first()
    if not district:
        raise HTTPException(status_code=404, detail="District not found")

    return (
        db.query(Constituency)
        .filter(Constituency.district_id == district_id)
        .order_by(Constituency.name)
        .all()
    )


@router.get("/areas")
def get_areas(
    constituency_id: int = Query(...),
    db: Session = Depends(get_db)
):
    constituency = (
        db.query(Constituency)
        .filter(Constituency.id == constituency_id)
        .first()
    )
    if not constituency:
        raise HTTPException(status_code=404, detail="Constituency not found")

    return (
        db.query(Area)
        .filter(Area.constituency_id == constituency_id)
        .order_by(Area.name)
        .all()
    )


@router.get("/booths")
def get_booths(
    area_id: int = Query(...),
    db: Session = Depends(get_db)
):
    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")

    return (
        db.query(Booth)
        .filter(Booth.area_id == area_id, Booth.status == "Active")
        .order_by(Booth.booth_number)
        .all()
    )
