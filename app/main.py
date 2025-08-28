# app/main.py
# Backend that issues QR WITHOUT requiring a pre-existing user.
# All person fields are OPTIONAL and stored on the QRToken row.

from fastapi import FastAPI, Form, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import qrcode

from app.db import SessionLocal
from app.models import QRToken, ScanLog
from app.config import TIMEZONE
from app.printer import print_qr_ticket  # uses your network printer
from io import BytesIO
import base64



app = FastAPI(title="QR KODU OLUSTURMA")

# ---------- DB session dependency ----------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- Constants / folders ----------
QR_DIR = Path("qr_images")
QR_DIR.mkdir(exist_ok=True)

ISSUER = "BenimGiriş"  # payload issuer string for QR data

# ---------- Health ----------
@app.get("/health")
def health():
    return {"ok": True, "service": "gate-entry", "status": "running"}

# ---------- Warmup on startup (faster first request) ----------
@app.on_event("startup")
def _warm_up():
    try:
        with SessionLocal() as db:
            db.execute("SELECT 1")
    except Exception as e:
        print("Warm DB fail:", e)

    # warm tz
    try:
        ZoneInfo(TIMEZONE)
    except Exception as e:
        print("Warm tz fail:", e)

    # warm qrcode + pillow
    try:
        qrcode.make("warmup-payload")
    except Exception as e:
        print("Warm QR fail:", e)

    # warm printer (optional; use if app.printer has _warm_printer)
    try:
        from app.printer import _warm_printer
        _warm_printer()
    except Exception:
        pass

# ---------- Issue QR WITHOUT user_id ----------
@app.post("/qr/issue")
def issue_qr(
    # All person fields optional:
    employee_id: str | None = Form(None),
    full_name:   str | None = Form(None),
    email:       str | None = Form(None),
    role:        str | None = Form(None),
    department:  str | None = Form(None),

    # QR controls:
    minutes_valid: int = Form(60),    # 0 = no expiry
    max_scans:     int = Form(2),     # >=1

    background: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    token = str(uuid4())

    # Use UTC-aware timestamps
    now = datetime.now(timezone.utc)
    exp = (now + timedelta(minutes=minutes_valid)) if minutes_valid and minutes_valid > 0 else None

    # Create row containing both token + person info
    rec = QRToken(
        token=token,
        issued_at=now.replace(tzinfo=None),       # store naive UTC in SQLite
        expires_at=exp.replace(tzinfo=None) if exp else None,
        status="active",
        max_scans=max_scans,
        scan_count=0,

        employee_id=employee_id,
        full_name=full_name,
        email=email,
        role=role,
        department=department,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    payload = f"{ISSUER}|{token}"
    # make small PNG in memory for instant web preview
    def _png_b64():
        buf = BytesIO()
        qrcode.make(payload).save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")

    # Save PNG (in background for speed)
    img_path = QR_DIR / f"{token}.png"
    def _render_png():
        qrcode.make(payload).save(img_path)

    # Build LOCAL time string for UI/print
    if exp:
        try:
            local_tz = ZoneInfo(TIMEZONE)
        except Exception:
            local_tz = datetime.now().astimezone().tzinfo
        exp_local = exp.astimezone(local_tz)
        exp_local_str = exp_local.strftime("%Y-%m-%d %H:%M:%S")
    else:
        exp_local_str = "No expiry"

    print_info = {
        "Kullancı Adı": rec.full_name,
        "Eposta": rec.email,
        "Görev": rec.role,
        "Kullancı No": rec.employee_id,
        "Bölüm": rec.department,
        "Aktif Okuma Sureci(Local)": exp_local_str,
        "Maksımum Okuma": rec.max_scans,
    }

    
    # Background: print + render PNG (non-blocking)
    '''  if background:
        background.add_task(print_qr_ticket, payload, print_info)
        background.add_task(_render_png)
    else:
        print_qr_ticket(payload, print_info)
        _render_png()'''
  
    def _render_png_to_disk():
        qrcode.make(payload).save(img_path)

    if background:
        background.add_task(print_qr_ticket, payload, print_info)
        background.add_task(_render_png_to_disk)
    else:
        print_qr_ticket(payload, print_info)
        _render_png_to_disk()

    return {
        "ok": True,
        "token": token,
        "payload": payload,
        "png_path": str(img_path),
        "qr_b64": _png_b64(),       # <— NEW: inline image for the web preview
        "print_info": print_info,
    }
# ---------- Serve QR PNG by token ----------
@app.get("/qr/png/{token}")
def get_qr_png(token: str):
    path = QR_DIR / f"{token}.png"
    if not path.exists():
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
    return FileResponse(path, media_type="image/png")

# ---------- Verify QR (payload = 'ISSUER|token') ----------
@app.post("/qr/verify")
def verify_qr(payload: dict, db: Session = Depends(get_db)):
    p = payload.get("payload", "")
    # Parse
    try:
        issuer, token = p.split("|", 1)
    except ValueError:
        _log_scan(db, token=None, result="denied:bad_payload")
        return {"ok": False, "reason": "bad_payload"}

    if issuer != ISSUER:
        _log_scan(db, token=token, result="denied:wrong_issuer")
        return {"ok": False, "reason": "wrong_issuer"}

    rec = db.query(QRToken).filter(QRToken.token == token).first()
    if not rec:
        _log_scan(db, token=token, result="denied:not_found")
        return {"ok": False, "reason": "not_found"}

    # status
    if rec.status != "active":
        _log_scan(db, token=token, result="denied:passive")
        return {"ok": False, "reason": "passive"}

    # expiry (stored as naive UTC)
    if rec.expires_at:
        exp_utc = rec.expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > exp_utc:
            rec.status = "passive"
            db.commit()
            _log_scan(db, token=token, result="denied:expired")
            return {"ok": False, "reason": "expired"}

    # scan count
    if rec.scan_count >= rec.max_scans:
        rec.status = "passive"
        db.commit()
        _log_scan(db, token=token, result="denied:max_scans_reached")
        return {"ok": False, "reason": "max_scans_reached"}

    # allow
    rec.scan_count += 1
    if rec.scan_count >= rec.max_scans:
        rec.status = "passive"
    db.commit()

    # optional hint for logs
    hint = rec.employee_id or rec.full_name or ""
    _log_scan(db, token=token, result="allowed", user_hint=hint)

    return {"ok": True, "scan_count": rec.scan_count, "status": rec.status}

def _log_scan(db: Session, token: str | None, result: str, user_hint: str | None = None):
    log = ScanLog(token=token or "", result=result, user_hint=user_hint or "")
    db.add(log)
    db.commit()

# ---------- Optional: simple status endpoint ----------
@app.get("/qr/status/{token}")
def qr_status(token: str, db: Session = Depends(get_db)):
    rec = db.query(QRToken).filter(QRToken.token == token).first()
    if not rec:
        return {"ok": False, "reason": "not_found"}
    return {
        "ok": True,
        "status": rec.status,
        "scan_count": rec.scan_count,
        "max_scans": rec.max_scans,
        "expires_at": rec.expires_at.isoformat() if rec.expires_at else None,
        "employee_id": rec.employee_id,
        "full_name": rec.full_name,
        "role": rec.role,
        "department": rec.department,
    }

# ---------- Redirect root to docs & serve web ----------
'''
@app.get("/")
def root():
    return RedirectResponse(url="/docs")

app.mount("/web", StaticFiles(directory="web", html=True), name="web")
'''
from fastapi.responses import RedirectResponse

@app.get("/")
def root():
    return RedirectResponse(url="/web/")

# Mount the /web static folder using an absolute path
WEB_DIR = Path(__file__).resolve().parent.parent / "web"   # points to F:/qr-code-gen/web
app.mount("/web", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
