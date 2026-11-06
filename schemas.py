from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


ROLES = {"Officer", "Verifier", "Booth Administrator"}


class UserRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4, max_length=100)
    role: str = Field("Officer")

    @field_validator("username")
    @classmethod
    def normalize_username(cls, v):
        v = v.strip().lower()
        if not v or " " in v:
            raise ValueError("Username must not contain spaces")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ROLES:
            raise ValueError(
                "New accounts may request Officer, Verifier, "
                "or Booth Administrator role"
            )
        return v



class UserLoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str = Field(validation_alias="full_name", serialization_alias="name")
    username: str
    role: str
    status: str
    created_at: datetime
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class VoterCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=120)
    dob: Optional[str] = None
    phone: str = Field(..., min_length=1, max_length=25)
    address: Optional[str] = None
    fingerprint_id: Optional[int] = None
    status: str = "Pending"
    photo: Optional[str] = None
    is_demo: int = 0

class VoterUpdate(BaseModel):
    id: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    dob: Optional[str] = None
    phone: Optional[str] = Field(None, min_length=1, max_length=25)
    address: Optional[str] = None
    fingerprint_id: Optional[int] = None
    status: Optional[str] = None
    photo: Optional[str] = None

class VoterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    dob: Optional[str] = None
    phone: str
    address: Optional[str] = None
    fingerprint_id: Optional[int] = None
    status: str
    photo: Optional[str] = None
    is_demo: int
    created_at: datetime
    updated_at: datetime

class AuditLogCreate(BaseModel):
    action: str = Field(..., min_length=1, max_length=1000)

class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: Optional[str] = None
    action: str
    timestamp: datetime
