import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base, SessionLocal

from .models import (
    User,
    Voter,
    State,
    District,
    Constituency,
    Area,
    Booth,
    BoothStaffAssignment,
    ElectionResultArchive,
)

from .auth import get_password_hash

from .routers import auth, admin, voters, audit, locations, assignments

Base.metadata.create_all(bind=engine)

app=FastAPI(title="SEAS Backend API",description="Smart Election Assurance System backend",version="1.0.0")

raw_origins=os.getenv("CORS_ORIGINS","http://127.0.0.1:3000,http://localhost:3000")
origins=[x.strip() for x in raw_origins.split(",") if x.strip()]
allow_all="*" in origins
app.add_middleware(CORSMiddleware,allow_origins=["*"] if allow_all else origins,allow_credentials=not allow_all,allow_methods=["*"],allow_headers=["*"])

@app.on_event("startup")
def startup():
    db=SessionLocal()
    try:
        username=os.getenv("DEFAULT_ADMIN_USERNAME","admin").strip().lower()
        if not db.query(User).filter(User.username==username).first():
            db.add(User(full_name=os.getenv("DEFAULT_ADMIN_NAME","System Administrator"),username=username,password_hash=get_password_hash(os.getenv("DEFAULT_ADMIN_PASSWORD","admin123")),role="Administrator",status="Approved"))
            db.commit()
    finally: db.close()

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(voters.router)
app.include_router(audit.router)
app.include_router(locations.router)
app.include_router(assignments.router)

@app.get("/api/health",tags=["Health Check"])
def health():
    return {"status":"healthy","service":"SEAS Backend API"}
