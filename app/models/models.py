import random
import string
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey,
    Text, Date, Enum as SAEnum, Boolean
)
from sqlalchemy.orm import relationship
from app.db.session import Base
import enum


def utcnow():
    return datetime.now(timezone.utc)


def generate_patient_id():
    digits = "".join(random.choices(string.digits, k=5))
    return f"PAT-{digits}"


class UserRole(str, enum.Enum):
    ROLE_DOCTOR = "ROLE_DOCTOR"
    ROLE_PATIENT = "ROLE_PATIENT"


class MedicationStatus(str, enum.Enum):
    active = "active"
    completed = "completed"


# ─────────────────────────── User ───────────────────────────
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    phone = Column(String(20), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(SAEnum(UserRole), nullable=False)
    patient_id = Column(String(20), ForeignKey("patients.patient_id"), nullable=True)

    patient = relationship("Patient", back_populates="user", foreign_keys=[patient_id])
    consultations = relationship("Consultation", back_populates="doctor", foreign_keys="Consultation.doctor_id")


# ─────────────────────────── Patient ───────────────────────────
class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(String(20), primary_key=True, default=generate_patient_id)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    dob = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="patient", foreign_keys=[User.patient_id])
    consultations = relationship("Consultation", back_populates="patient", cascade="all, delete-orphan")


# ─────────────────────────── Consultation ───────────────────────────
class Consultation(Base):
    __tablename__ = "consultations"

    consultation_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String(20), ForeignKey("patients.patient_id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    audio_url = Column(String(500), nullable=True)
    transcript = Column(Text, nullable=True)
    soap_note = Column(Text, nullable=True)         # stored as JSON string
    doctor_summary = Column(Text, nullable=True)
    patient_summary = Column(Text, nullable=True)
    date = Column(Date, nullable=False, default=lambda: datetime.now(timezone.utc).date())
    created_at = Column(DateTime(timezone=True), default=utcnow)

    patient = relationship("Patient", back_populates="consultations")
    doctor = relationship("User", back_populates="consultations", foreign_keys=[doctor_id])
    diagnoses = relationship("Diagnosis", back_populates="consultation", cascade="all, delete-orphan")
    medications = relationship("Medication", back_populates="consultation", cascade="all, delete-orphan")


# ─────────────────────────── Diagnosis ───────────────────────────
class Diagnosis(Base):
    __tablename__ = "diagnoses"

    diagnosis_id = Column(Integer, primary_key=True, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.consultation_id"), nullable=False)
    diagnosis_name = Column(String(500), nullable=False)
    severity = Column(String(50), nullable=True)

    consultation = relationship("Consultation", back_populates="diagnoses")


# ─────────────────────────── Medication ───────────────────────────
class Medication(Base):
    __tablename__ = "medications"

    medication_id = Column(Integer, primary_key=True, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.consultation_id"), nullable=False)
    medicine_name = Column(String(255), nullable=False)
    dosage = Column(String(100), nullable=True)
    duration = Column(String(100), nullable=True)
    status = Column(SAEnum(MedicationStatus), default=MedicationStatus.active)

    consultation = relationship("Consultation", back_populates="medications")


# ─────────────────────────── OTP Store ───────────────────────────
class OTPStore(Base):
    __tablename__ = "otp_store"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), nullable=False, index=True)
    otp_code = Column(String(10), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
