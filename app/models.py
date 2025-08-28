# app/models.py
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.db import Base

class QRToken(Base):
    __tablename__ = "qr_tokens"

    id = Column(Integer, primary_key=True, index=True)

    # core token
    token = Column(String, unique=True, index=True, nullable=False)
    issued_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    status = Column(String, default="active")   # active | passive
    max_scans = Column(Integer, default=1)
    scan_count = Column(Integer, default=0)

    # person info (all OPTIONAL; provided directly from the web form)
    employee_id = Column(String, nullable=True)
    full_name   = Column(String, nullable=True)
    email       = Column(String, nullable=True)
    role        = Column(String, nullable=True)
    department  = Column(String, nullable=True)

class ScanLog(Base):
    __tablename__ = "scan_logs"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, index=True)          # the token that was scanned
    result = Column(String)                     # "allowed" or "denied:*"
    user_hint = Column(String, nullable=True)   # e.g., employee_id/full_name (optional)
    ts = Column(DateTime, default=datetime.utcnow)