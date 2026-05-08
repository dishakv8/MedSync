from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from app.db.session import get_db
from app.models.models import Patient, Consultation, User, generate_patient_id
from app.schemas.schemas import PatientCreate, PatientOut, TimelineEntry
from app.api.deps import require_doctor, require_patient, get_current_user
from app.core.responses import success_response, error_response
from typing import List

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("/")
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    doctor: User = Depends(require_doctor),
):
    pid = generate_patient_id()
    while db.query(Patient).filter(Patient.patient_id == pid).first():
        pid = generate_patient_id()

    patient = Patient(
        patient_id=pid,
        name=payload.name,
        phone=payload.phone,
        dob=payload.dob,
        gender=payload.gender,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    return success_response(
        data=PatientOut.model_validate(patient).model_dump(mode="json"),
        message="Patient registered",
        status_code=201,
    )


@router.get("/search")
def search_patients(
    q: str = "",
    db: Session = Depends(get_db),
    doctor: User = Depends(require_doctor),
):
    results = (
        db.query(Patient)
        .filter(
            or_(
                Patient.name.ilike(f"%{q}%"),
                Patient.phone.ilike(f"%{q}%"),
                Patient.patient_id.ilike(f"%{q}%"),
            )
        )
        .limit(20)
        .all()
    )
    data = [PatientOut.model_validate(p).model_dump(mode="json") for p in results]
    return success_response(data=data)


@router.get("/{patient_id}")
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Doctors can see any patient; patients can only see themselves
    if current_user.role.value == "ROLE_PATIENT" and current_user.patient_id != patient_id:
        return error_response("Access denied", 403)

    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        return error_response("Patient not found", 404)

    return success_response(data=PatientOut.model_validate(patient).model_dump(mode="json"))


@router.get("/{patient_id}/timeline")
def get_patient_timeline(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Patients can only view their own timeline
    if current_user.role.value == "ROLE_PATIENT" and current_user.patient_id != patient_id:
        return error_response("Access denied", 403)

    consultations = (
        db.query(Consultation)
        .options(joinedload(Consultation.diagnoses), joinedload(Consultation.medications))
        .filter(Consultation.patient_id == patient_id)
        .order_by(Consultation.date.desc())
        .all()
    )

    timeline = [TimelineEntry.model_validate(c).model_dump(mode="json") for c in consultations]
    return success_response(data=timeline)
