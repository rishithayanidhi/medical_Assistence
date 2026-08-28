"""
Database models for MediPulse AI.

Uses SQLAlchemy Core with a lightweight SQLite backend by default.
Switch DATABASE_URL to a PostgreSQL connection string for production use.

Usage:
    from database.models import Base, engine, Prescription
    Base.metadata.create_all(engine)   # Creates tables on first run
"""

import os
import json
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Float,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# ---------------------------------------------------------------------------
# Engine — defaults to a local SQLite file; override via DATABASE_URL env var
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./medipulse.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Prescription record — one row per uploaded document
# ---------------------------------------------------------------------------
class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    raw_text = Column(Text, nullable=True)
    ocr_quality = Column(String(10), nullable=True)     # HIGH | MEDIUM | LOW
    ocr_avg_confidence = Column(Float, nullable=True)

    # JSON-serialised lists stored as text columns
    medications = Column(Text, nullable=True)           # JSON list
    unverified_medications = Column(Text, nullable=True)  # JSON list
    diagnoses = Column(Text, nullable=True)             # JSON list
    dosages = Column(Text, nullable=True)               # JSON list
    frequencies = Column(Text, nullable=True)           # JSON list

    # Patient metadata (may be None if not detected)
    patient_name = Column(String(255), nullable=True)
    doctor_name = Column(String(255), nullable=True)
    prescription_date = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # -- Helpers --

    def set_medications(self, meds: list):
        self.medications = json.dumps(meds)

    def get_medications(self) -> list:
        return json.loads(self.medications) if self.medications else []

    def set_diagnoses(self, diags: list):
        self.diagnoses = json.dumps(diags)

    def get_diagnoses(self) -> list:
        return json.loads(self.diagnoses) if self.diagnoses else []

    def __repr__(self):
        return f"<Prescription id={self.id} file='{self.filename}' quality='{self.ocr_quality}'>"


# ---------------------------------------------------------------------------
# Patient record — for future multi-prescription patient tracking
# ---------------------------------------------------------------------------
class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    doctor_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Patient id={self.id} name='{self.name}'>"


def get_db():
    """FastAPI dependency: yields a database session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
