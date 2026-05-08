import os
import json
import shutil
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from app.db.session import get_db
from app.models.models import Consultation, Patient, User, Diagnosis, Medication, MedicationStatus
from app.schemas.schemas import (
    ConsultationCreate, ConsultationOut, ConsultationPatientView, TimelineEntry
)
from app.api.deps import require_doctor, get_current_user
from app.core.responses import success_response, error_response
from app.core.config import settings
from app.services.gemini_service import process_transcript_with_gemini
from app.services.whisper_service import transcribe_audio

router = APIRouter(prefix="/consultations", tags=["consultations"])


def _load_consultation(consultation_id: int, db: Session) -> Consultation:
    c = (
        db.query(Consultation)
        .options(joinedload(Consultation.diagnoses), joinedload(Consultation.medications))
        .filter(Consultation.consultation_id == consultation_id)
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Consultation not found")
    return c


def _serialize_consultation(c: Consultation) -> dict:
    data = ConsultationOut.model_validate(c).model_dump(mode="json")
    # Parse soap_note from JSON string if needed
    if isinstance(data.get("soap_note"), str):
        try:
            data["soap_note"] = json.loads(data["soap_note"])
        except Exception:
            pass
    return data


@router.post("/")
def create_consultation(
    payload: ConsultationCreate,
    db: Session = Depends(get_db),
    doctor: User = Depends(require_doctor),
):
    patient = db.query(Patient).filter(Patient.patient_id == payload.patient_id).first()
    if not patient:
        return error_response("Patient not found", 404)

    consultation = Consultation(
        patient_id=payload.patient_id,
        doctor_id=doctor.user_id,
        date=payload.date or datetime.utcnow().date(),
    )
    db.add(consultation)
    db.commit()
    db.refresh(consultation)

    return success_response(
        data={"consultation_id": consultation.consultation_id},
        message="Consultation created",
        status_code=201,
    )


@router.post("/{consultation_id}/upload-audio")
async def upload_audio(
    consultation_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    doctor: User = Depends(require_doctor),
):
    consultation = _load_consultation(consultation_id, db)

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    filename = f"consult_{consultation_id}_{file.filename}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    consultation.audio_url = filepath
    db.commit()

    return success_response(
        data={"audio_url": filepath},
        message="Audio uploaded successfully",
    )


@router.post("/{consultation_id}/transcribe")
async def transcribe_consultation(
    consultation_id: int,
    db: Session = Depends(get_db),
    doctor: User = Depends(require_doctor),
):
    consultation = _load_consultation(consultation_id, db)

    if not consultation.audio_url:
        return error_response("No audio uploaded for this consultation", 400)

    transcript = await transcribe_audio(consultation.audio_url)
    if not transcript:
        return error_response("Transcription failed", 500)

    consultation.transcript = transcript
    db.commit()

    return success_response(
        data={"transcript": transcript},
        message="Transcription complete",
    )


@router.post("/{consultation_id}/process")
async def process_consultation(
    consultation_id: int,
    db: Session = Depends(get_db),
    doctor: User = Depends(require_doctor),
):
    consultation = _load_consultation(consultation_id, db)

    if not consultation.transcript:
        return error_response("No transcript found. Run /transcribe first.", 400)

    extracted = await process_transcript_with_gemini(consultation.transcript)
    if not extracted:
        return error_response("AI processing failed. Check Gemini API key.", 500)

    # Clear existing diagnoses and medications for idempotency
    db.query(Diagnosis).filter(Diagnosis.consultation_id == consultation_id).delete()
    db.query(Medication).filter(Medication.consultation_id == consultation_id).delete()

    # Store diagnosis
    if extracted.diagnosis:
        diagnosis = Diagnosis(
            consultation_id=consultation_id,
            diagnosis_name=extracted.diagnosis,
            severity=extracted.severity,
        )
        db.add(diagnosis)

    # Store medications
    for med in extracted.medications:
        medication = Medication(
            consultation_id=consultation_id,
            medicine_name=med.get("name", ""),
            dosage=med.get("dosage", ""),
            duration=med.get("duration", ""),
            status=MedicationStatus.active,
        )
        db.add(medication)

    # Update consultation
    consultation.soap_note = json.dumps(extracted.soap_note.model_dump())
    consultation.doctor_summary = extracted.doctor_summary
    consultation.patient_summary = extracted.patient_summary

    db.commit()

    return success_response(
        data={
            "symptoms": extracted.symptoms,
            "diagnosis": extracted.diagnosis,
            "severity": extracted.severity,
            "followup_days": extracted.followup_days,
            "soap_note": extracted.soap_note.model_dump(),
            "doctor_summary": extracted.doctor_summary,
            "patient_summary": extracted.patient_summary,
            "medications_stored": len(extracted.medications),
        },
        message="Consultation processed successfully",
    )


@router.get("/{consultation_id}")
def get_consultation(
    consultation_id: int,
    db: Session = Depends(get_db),
    doctor: User = Depends(require_doctor),
):
    consultation = _load_consultation(consultation_id, db)
    return success_response(data=_serialize_consultation(consultation))


@router.get("/{consultation_id}/patient-view")
def get_consultation_patient_view(
    consultation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    consultation = _load_consultation(consultation_id, db)

    # Patients can only view their own consultations
    if current_user.role.value == "ROLE_PATIENT":
        if current_user.patient_id != consultation.patient_id:
            return error_response("Access denied", 403)

    data = ConsultationPatientView.model_validate(consultation).model_dump(mode="json")
    return success_response(data=data)
