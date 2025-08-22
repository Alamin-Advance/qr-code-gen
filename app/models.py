from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db import Base

from sqlalchemy import Column, Integer, String, Boolean
from app.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # OPTIONAL, can be duplicated
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)  # <- NO unique, NO index

    # OPTIONAL text, we validate dropdown in API (can be duplicated)
    role = Column(String, default="Employee", nullable=True)

    is_active = Column(Boolean, default=True)

    # ONLY this is unique & required
    employee_id = Column(String, unique=True, index=True, nullable=False)

    # OPTIONAL dropdown (can be duplicated)
    department = Column(String, nullable=True)

class QRToken(Base):
    __tablename__ = "qr_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    token = Column(String, unique=True, index=True)
    issued_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    status = Column(String, default="active")   # active / passive
    max_scans = Column(Integer, default=2)
    scan_count = Column(Integer, default=0)

    user = relationship("User")

Index("idx_qr_token_status", QRToken.token, QRToken.status)

# app/models.py 
from sqlalchemy import DateTime
from datetime import datetime

class ScanLog(Base):
    __tablename__ = "scan_logs"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, index=True)
    user_id = Column(Integer, index=True)
    scanned_at = Column(DateTime, default=datetime.utcnow)
    result = Column(String)  # "allowed" | "denied:<reason>"
