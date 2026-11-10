
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import VoteTally, Booth, User, ElectionResultArchive
from app.dependencies import get_current_user, require_main_admin

router = APIRouter(
    prefix="/api/results",
    tags=["Election Results"]
)


class VoteTallyInput(BaseModel):
    election_cycle: str
    booth_id: int
    party_name: str
    vote_count: int = Field(ge=0)


@router.post("/tallies")
def save_tally(
    data: VoteTallyInput,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    booth = db.query(Booth).filter(
        Booth.id == data.booth_id
    ).first()

    if not booth:
        raise HTTPException(404, "Booth not found")

    party = data.party_name.strip()
    if not party:
        raise HTTPException(400, "Party name is required")

    tally = db.query(VoteTally).filter(
        VoteTally.election_cycle == data.election_cycle,
        VoteTally.booth_id == data.booth_id,
        func.lower(VoteTally.party_name) == party.lower()
    ).first()

    if tally:
        tally.vote_count = data.vote_count
        tally.recorded_by = user.id
    else:
        tally = VoteTally(
            election_cycle=data.election_cycle,
            booth_id=data.booth_id,
            party_name=party,
            vote_count=data.vote_count,
            recorded_by=user.id
        )
        db.add(tally)

    db.commit()
    db.refresh(tally)

    return {
        "message": "Election tally saved",
        "booth_id": tally.booth_id,
        "party_name": tally.party_name,
        "vote_count": tally.vote_count
    }


@router.get("")
def get_results(
    election_cycle: str,
    db: Session = Depends(get_db),
    admin=Depends(require_main_admin)
):
    # Check whether this election has archived results
    archived = db.query(ElectionResultArchive).filter(
        ElectionResultArchive.election_cycle == election_cycle
    ).all()

    if archived:
        totals = {}
        for row in archived:
            totals[row.party_name] = (
                totals.get(row.party_name, 0) + row.vote_count
            )

        return {
            "election_cycle": election_cycle,
            "party_totals": [
                {"party_name": party, "total_votes": votes}
                for party, votes in totals.items()
            ],
            "total_votes": sum(totals.values()),
            "source": "archive"
        }

    # Otherwise, read the current tallies for this election
    rows = db.query(
        VoteTally.party_name,
        func.sum(VoteTally.vote_count).label("total_votes")
    ).filter(
        VoteTally.election_cycle == election_cycle
    ).group_by(
        VoteTally.party_name
    ).all()

    return {
        "election_cycle": election_cycle,
        "party_totals": [
            {
                "party_name": row.party_name,
                "total_votes": row.total_votes
            }
            for row in rows
        ],
        "total_votes": sum(row.total_votes for row in rows),
        "source": "current"
    }