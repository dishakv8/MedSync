import json
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from app.db.session import get_db
from app.models.models import Consultation, Patient, User, Diagnosis
from app.api.deps import require_doctor
from app.core.responses import success_response, error_response
from app.services.gemini_service import generate_patient_insights
from app.schemas.schemas import InsightObject

router = APIRouter(tags=["insights"])

# Symptom keyword groups for pattern matching
SYMPTOM_GROUPS = {
    "respiratory": ["cough", "wheeze", "breathe", "breath", "lung", "bronch", "respiratory", "asthma", "pneumonia"],
    "gastrointestinal": ["nausea", "vomit", "diarrhea", "stomach", "abdomin", "bowel", "gastro", "constip"],
    "fever": ["fever", "temperature", "pyrexia", "febrile"],
    "pain": ["pain", "ache", "hurt", "sore", "discomfort"],
    "skin": ["rash", "itch", "skin", "dermat", "hives", "eczema"],
    "neurological": ["headache", "migraine", "dizzy", "neuro", "seizure", "numb"],
    "cardiac": ["chest", "heart", "cardiac", "palpitat", "tachycard"],
}


def _classify_symptom(text: str) -> list[str]:
    text_lower = text.lower()
    groups = []
    for group, keywords in SYMPTOM_GROUPS.items():
        if any(kw in text_lower for kw in keywords):
            groups.append(group)
    return groups or ["other"]


def _rule_based_insights(consultations: list) -> list:
    """Fast in-house pattern detection (no AI required)."""
    insights = []
    now = datetime.now(timezone.utc).date()
    cutoff = now - timedelta(days=90)

    # Group by symptom category across consultations
    category_visits: dict[str, list] = defaultdict(list)

    for c in consultations:
        if c.date < cutoff:
            continue
        # Pull symptoms from soap_note subjective field
        symptoms_text = ""
        if c.soap_note:
            try:
                soap = json.loads(c.soap_note) if isinstance(c.soap_note, str) else c.soap_note
                symptoms_text = soap.get("subjective", "")
            except Exception:
                pass

        # Also check diagnosis names
        for d in c.diagnoses:
            symptoms_text += " " + d.diagnosis_name

        for category in set(_classify_symptom(symptoms_text)):
            category_visits[category].append(c)

    for category, visits in category_visits.items():
        if len(visits) >= 2:
            severity = "high" if len(visits) >= 4 else "moderate" if len(visits) >= 3 else "low"
            insights.append({
                "type": "recurring",
                "message": f"Recurring {category} symptoms detected across {len(visits)} visit(s) in the last 90 days.",
                "severity": severity,
            })

    return insights


@router.get("/patients/{patient_id}/insights")
async def get_patient_insights(
    patient_id: str,
    use_ai: bool = False,
    db: Session = Depends(get_db),
    doctor: User = Depends(require_doctor),
):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        return error_response("Patient not found", 404)

    consultations = (
        db.query(Consultation)
        .options(joinedload(Consultation.diagnoses), joinedload(Consultation.medications))
        .filter(Consultation.patient_id == patient_id)
        .order_by(Consultation.date.desc())
        .all()
    )

    if not consultations:
        return success_response(data=[], message="No consultations found")

    if use_ai:
        # Build history JSON for Gemini
        history = []
        for c in consultations:
            history.append({
                "date": str(c.date),
                "diagnoses": [d.diagnosis_name for d in c.diagnoses],
                "doctor_summary": c.doctor_summary or "",
                "soap_note": c.soap_note or "",
            })
        insights = await generate_patient_insights(json.dumps(history, indent=2))
    else:
        insights = _rule_based_insights(consultations)

    return success_response(
        data=insights,
        message=f"{len(insights)} insight(s) found",
    )
