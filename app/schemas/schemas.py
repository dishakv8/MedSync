from __future__ import annotations
from datetime import date, datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, field_validator
from app.models.models import UserRole, MedicationStatus


# ─────────────────────────── Auth ───────────────────────────
class RegisterRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: str
    role: UserRole
    name: Optional[str] = None          # required for patients registering directly

    @field_validator("role")
    @classmethod
    def check_contact(cls, v):
        return v


class LoginRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: str


class OTPSendRequest(BaseModel):
    phone: str


class OTPVerifyRequest(BaseModel):
    phone: str
    otp: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int


# ─────────────────────────── Patient ───────────────────────────
class PatientCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None


class PatientOut(BaseModel):
    patient_id: str
    name: str
    phone: Optional[str]
    dob: Optional[date]
    gender: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────── Medication ───────────────────────────
class MedicationOut(BaseModel):
    medication_id: int
    medicine_name: str
    dosage: Optional[str]
    duration: Optional[str]
    status: MedicationStatus

    model_config = {"from_attributes": True}


# ─────────────────────────── Diagnosis ───────────────────────────
class DiagnosisOut(BaseModel):
    diagnosis_id: int
    diagnosis_name: str
    severity: Optional[str]

    model_config = {"from_attributes": True}


# ─────────────────────────── Consultation ───────────────────────────
class ConsultationCreate(BaseModel):
    patient_id: str
    date: Optional[date] = None


class SOAPNote(BaseModel):
    subjective: str = ""
    objective: str = ""
    assessment: str = ""
    plan: str = ""


class ConsultationOut(BaseModel):
    consultation_id: int
    patient_id: str
    doctor_id: int
    audio_url: Optional[str]
    transcript: Optional[str]
    soap_note: Optional[Any]
    doctor_summary: Optional[str]
    patient_summary: Optional[str]
    date: date
    created_at: datetime
    diagnoses: List[DiagnosisOut] = []
    medications: List[MedicationOut] = []

    model_config = {"from_attributes": True}


class ConsultationPatientView(BaseModel):
    consultation_id: int
    date: date
    patient_summary: Optional[str]
    medications: List[MedicationOut] = []
    diagnoses: List[DiagnosisOut] = []

    model_config = {"from_attributes": True}


# ─────────────────────────── Timeline ───────────────────────────
class TimelineEntry(BaseModel):
    consultation_id: int
    date: date
    doctor_summary: Optional[str]
    patient_summary: Optional[str]
    diagnoses: List[DiagnosisOut] = []
    medications: List[MedicationOut] = []

    model_config = {"from_attributes": True}


# ─────────────────────────── Insights ───────────────────────────
class InsightObject(BaseModel):
    type: str
    message: str
    severity: str


# ─────────────────────────── AI Pipeline ───────────────────────────
class AIExtractedData(BaseModel):
    symptoms: List[str] = []
    diagnosis: str = ""
    severity: str = ""
    medications: List[dict] = []
    followup_days: int = 0
    soap_note: SOAPNote = SOAPNote()
    doctor_summary: str = ""
    patient_summary: str = ""
