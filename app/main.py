# app/main.py
# Minimal API to create users, issue QR, verify scans, and serve QR PNGs.

from enum import Enum
from typing import Optional, Annotated
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import qrcode
from fastapi import FastAPI, Form, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import User, QRToken, ScanLog

app = FastAPI(title="Gate Entry API")

# -------------------------
# DB session dependency
# -------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------------
# Health check
# -------------------------
@app.get("/health")
def health():
    return {"ok": True, "service": "gate-entry", "status": "running"}

# -------------------------
# Dropdown enums (Swagger will render as select boxes)
# -------------------------
class RoleEnum(str, Enum):
    Admin = "Admin"
    Staff = "Staff"
    Visitor = "Visitor"
    Security = "Security"

class DepartmentEnum(str, Enum):
    DataAnalyst = "Data Analyst"
    DataScientist = "Data Scientist"
    HR = "HR"
    MLEngineer = "ML Engineer"
    SoftwareEngineer = "Software Engineer"
    SecurityDept = "Security"
    Operations = "Operations"
    Support = "Support"
    Finance = "Finance"
    Marketing = "Marketing"
    Sales = "Sales"
    Product = "Product"
    QA = "QA"
    Other = "Other"

# -------------------------
# Create a user
# - full_name, email: optional
# - employee_id: required & unique
# - role, department: optional dropdowns (Enums)
# -------------------------
@app.post("/users/create")
def create_user(
    # OPTIONAL text fields
    full_name:   Annotated[Optional[str], Form()] = None,
    email:       Annotated[Optional[str], Form()] = None,

    # OPTIONAL dropdowns (Enums). Swagger shows selects for these.
    role:        Annotated[Optional[RoleEnum], Form()] = None,
    department:  Annotated[Optional[DepartmentEnum], Form()] = None,

    # REQUIRED
    employee_id: Annotated[str, Form()] = ...,

    db: Session = Depends(get_db),
):
    # enforce unique employee_id
    existing = db.query(User).filter(User.employee_id == employee_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="employee_id already exists")

    user = User(
        full_name=full_name,
        email=email,
        role=(role.value if role else "Employee"),
        employee_id=employee_id,
        department=(department.value if department else None),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"ok": True, "user_id": user.id}

# -------------------------
# Issue a QR for a user and save PNG
# -------------------------
QR_DIR = Path("qr_images")
QR_DIR.mkdir(exist_ok=True)

ISSUER = "MyCompanyGate"  # issuer prefix in the QR payload

@app.post("/qr/issue")
def issue_qr(
    user_id: int = Form(...),
    minutes_valid: int = Form(60),
    max_scans: int = Form(2),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse({"ok": False, "error": "user_not_found"}, status_code=404)

    token = str(uuid4())
    now = datetime.utcnow()
    exp = now + timedelta(minutes=minutes_valid) if minutes_valid and minutes_valid > 0 else None

    rec = QRToken(
        user_id=user_id,
        token=token,
        issued_at=now,
        expires_at=exp,
        status="active",
        max_scans=max_scans,
        scan_count=0,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    payload = f"{ISSUER}|{token}"
    img_path = QR_DIR / f"{token}.png"
    qrcode.make(payload).save(img_path)

    return {
        "ok": True,
        "token": token,
        "payload": payload,
        "png_path": str(img_path),
        "print_info": {
            "Full Name": user.full_name,
            "Email": user.email,
            "Role": user.role,
            "Employee ID": user.employee_id,
            "Department": user.department,
            "Valid Until (UTC)": exp.isoformat() if exp else "No expiry",
            "Max Scans": rec.max_scans,
        },
    }

# -------------------------
# Serve QR PNG by token
# -------------------------
@app.get("/qr/png/{token}")
def get_qr_png(token: str):
    path = QR_DIR / f"{token}.png"
    if not path.exists():
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
    return FileResponse(path, media_type="image/png")

# -------------------------
# Verify QR (enforce expiry, max scans, passive)
# -------------------------
class VerifyIn(BaseModel):
    payload: str  # expects "MyCompanyGate|<token>"

def _log_scan(db: Session, token: Optional[str], user_id: Optional[int], result: str):
    log = ScanLog(token=token or "", user_id=user_id or 0, result=result)
    db.add(log)
    db.commit()

@app.post("/qr/verify")
def verify_qr(body: VerifyIn, db: Session = Depends(get_db)):
    # 1) Parse payload
    try:
        issuer, token = body.payload.split("|", 1)
    except ValueError:
        _log_scan(db, token=None, user_id=None, result="denied:bad_payload")
        return {"ok": False, "reason": "bad_payload"}

    if issuer != ISSUER:
        _log_scan(db, token=token, user_id=None, result="denied:wrong_issuer")
        return {"ok": False, "reason": "wrong_issuer"}

    # 2) Find token row
    rec = db.query(QRToken).filter(QRToken.token == token).first()
    if not rec:
        _log_scan(db, token=token, user_id=None, result="denied:not_found")
        return {"ok": False, "reason": "not_found"}

    # 3) Status / expiry checks
    if rec.status != "active":
        _log_scan(db, token=token, user_id=rec.user_id, result="denied:passive")
        return {"ok": False, "reason": "passive"}

    if rec.expires_at and datetime.utcnow() > rec.expires_at:
        rec.status = "passive"
        db.commit()
        _log_scan(db, token=token, user_id=rec.user_id, result="denied:expired")
        return {"ok": False, "reason": "expired"}

    # 4) Scan count check
    if rec.scan_count >= rec.max_scans:
        rec.status = "passive"
        db.commit()
        _log_scan(db, token=token, user_id=rec.user_id, result="denied:max_scans_reached")
        return {"ok": False, "reason": "max_scans_reached"}

    # 5) Allow this scan; possibly flip to passive
    rec.scan_count += 1
    if rec.scan_count >= rec.max_scans:
        rec.status = "passive"
    db.commit()

    _log_scan(db, token=token, user_id=rec.user_id, result="allowed")
    return {"ok": True, "user_id": rec.user_id, "scan_count": rec.scan_count, "status": rec.status}

# -------------------------
# Handy status endpoint
# -------------------------
@app.get("/qr/status/{token}")
def qr_status(token: str, db: Session = Depends(get_db)):
    rec = db.query(QRToken).filter(QRToken.token == token).first()
    if not rec:
        return {"ok": False, "reason": "not_found"}
    return {
        "ok": True,
        "user_id": rec.user_id,
        "status": rec.status,
        "scan_count": rec.scan_count,
        "max_scans": rec.max_scans,
        "expires_at": rec.expires_at.isoformat() if rec.expires_at else None,
    }

# -------------------------
# Root → docs, and serve /web
# -------------------------
@app.get("/")
def root():
    return RedirectResponse(url="/docs")

app.mount("/web", StaticFiles(directory="web", html=True), name="web")