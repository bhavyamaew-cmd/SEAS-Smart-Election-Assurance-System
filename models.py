from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False, default="Officer")
    status = Column(String(20), nullable=False, default="Pending", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    approved_by = Column(String(50), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejected_by = Column(String(50), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Voter(Base):
    __tablename__ = "voters"
    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    dob = Column(String(20), nullable=True)
    phone = Column(String(25), nullable=False)
    address = Column(Text, nullable=True)
    fingerprint_id = Column(Integer, unique=True, nullable=True, index=True)
    status = Column(String(20), nullable=False, default="Pending", index=True)
    photo = Column(Text, nullable=True)
    is_demo = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    username = Column(String(50), nullable=True, index=True)
    action = Column(Text, nullable=False)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)

Index("ix_users_status_created", User.status, User.created_at)


class State(Base):
    __tablename__ = "states"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(10), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)



class District(Base):
    __tablename__ = "districts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    state_id = Column(Integer, ForeignKey("states.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Constituency(Base):
    __tablename__ = "constituencies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    district_id = Column(
        Integer,
        ForeignKey("districts.id"),
        nullable=False,
        index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    
class Area(Base):
    __tablename__ = "areas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    constituency_id = Column(
        Integer,
        ForeignKey("constituencies.id"),
        nullable=False,
        index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Booth(Base):
    __tablename__ = "booths"

    id = Column(Integer, primary_key=True, index=True)
    booth_number = Column(String(30), nullable=False)
    name = Column(String(150), nullable=True)
    area_id = Column(
        Integer,
        ForeignKey("areas.id"),
        nullable=False,
        index=True
    )
    status = Column(String(20), nullable=False, default="Active")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class BoothStaffAssignment(Base):
    __tablename__ = "booth_staff_assignments"

    id = Column(Integer, primary_key=True, index=True)
    booth_id = Column(
        Integer,
        ForeignKey("booths.id"),
        nullable=False,
        index=True
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    role = Column(String(30), nullable=False)
    election_cycle = Column(String(30), nullable=False, index=True)
    assigned_by = Column(String(50), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(20), nullable=False, default="Active")


class VoteTally(Base):
    __tablename__ = "vote_tallies"

    id = Column(Integer, primary_key=True, index=True)

    election_cycle = Column(String(30), nullable=False, index=True)

    booth_id = Column(
        Integer,
        ForeignKey("booths.id"),
        nullable=False,
        index=True
    )

    party_name = Column(String(150), nullable=False)

    vote_count = Column(Integer, nullable=False, default=0)

    recorded_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    recorded_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        Index(
            "uq_vote_tally_cycle_booth_party",
            "election_cycle",
            "booth_id",
            "party_name",
            unique=True
        ),
    )


class ElectionResultArchive(Base):
    __tablename__ = "election_result_archives"

    id = Column(Integer, primary_key=True, index=True)

    election_cycle = Column(String(30), nullable=False, index=True)
    booth_id = Column(Integer, ForeignKey("booths.id"), nullable=False)
    party_name = Column(String(150), nullable=False)
    vote_count = Column(Integer, nullable=False, default=0)

    # Historical turnout snapshot for this booth
    registered_voters = Column(Integer, nullable=False, default=0)
    voters_voted = Column(Integer, nullable=False, default=0)
    voters_not_voted = Column(Integer, nullable=False, default=0)

    archived_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        Index(
            "uq_archive_cycle_booth_party",
            "election_cycle",
            "booth_id",
            "party_name",
            unique=True
        ),
    )
