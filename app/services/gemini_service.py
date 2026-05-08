import json
import re
from typing import Optional
import google.generativeai as genai
from app.core.config import settings
from app.schemas.schemas import AIExtractedData

genai.configure(api_key=settings.GEMINI_API_KEY)

EXTRACTION_PROMPT = """You are a medical AI assistant. Given the following doctor-patient consultation transcript, extract structured medical information.

Return ONLY a valid JSON object with NO markdown, NO code fences, NO preamble. The JSON must follow this exact schema:

{{
  "symptoms": ["list of symptoms mentioned"],
  "diagnosis": "primary diagnosis",
  "severity": "mild | moderate | severe",
  "medications": [
    {{"name": "medicine name", "dosage": "dosage string", "duration": "duration string"}}
  ],
  "followup_days": 7,
  "soap_note": {{
    "subjective": "patient reported symptoms and history",
    "objective": "objective findings, vitals, exam results",
    "assessment": "diagnosis and clinical assessment",
    "plan": "treatment plan and follow-up"
  }},
  "doctor_summary": "Clinical summary for the treating physician (2-3 sentences, medical terminology OK)",
  "patient_summary": "Simple explanation for the patient (plain language, 2-3 sentences)"
}}

Transcript:
{transcript}
"""

INSIGHTS_PROMPT = """You are a medical AI. Analyze the following consultation history for a patient and identify recurring symptoms or diagnosis patterns.

History (JSON):
{history}

Identify recurring patterns (same symptom/diagnosis in 2+ visits within 90 days). Return ONLY a JSON array of insight objects:

[
  {{
    "type": "recurring",
    "message": "Descriptive message about the pattern",
    "severity": "low | moderate | high"
  }}
]

If no patterns, return an empty array: []
"""


def extract_json_from_response(text: str) -> dict:
    """Strip any markdown fences and parse JSON."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


async def process_transcript_with_gemini(transcript: str) -> Optional[AIExtractedData]:
    """Call Gemini to extract structured data from transcript."""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = EXTRACTION_PROMPT.format(transcript=transcript)
        response = model.generate_content(prompt)
        raw = response.text
        data = extract_json_from_response(raw)

        # Normalize soap_note
        soap = data.get("soap_note", {})
        from app.schemas.schemas import SOAPNote
        soap_note = SOAPNote(
            subjective=soap.get("subjective", ""),
            objective=soap.get("objective", ""),
            assessment=soap.get("assessment", ""),
            plan=soap.get("plan", ""),
        )

        return AIExtractedData(
            symptoms=data.get("symptoms", []),
            diagnosis=data.get("diagnosis", ""),
            severity=data.get("severity", "mild"),
            medications=data.get("medications", []),
            followup_days=int(data.get("followup_days", 7)),
            soap_note=soap_note,
            doctor_summary=data.get("doctor_summary", ""),
            patient_summary=data.get("patient_summary", ""),
        )
    except Exception as e:
        print(f"[Gemini] Error processing transcript: {e}")
        return None


async def generate_patient_insights(history_json: str) -> list:
    """Call Gemini to detect recurring patterns across consultations."""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = INSIGHTS_PROMPT.format(history=history_json)
        response = model.generate_content(prompt)
        data = extract_json_from_response(response.text)
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[Gemini] Error generating insights: {e}")
        return []
