"""
seed.py — Populate demo data for hackathon presentation.

Usage:
    python seed.py

Creates:
  - 1 doctor account  (email: doctor@demo.com | password: Demo@1234)
  - 2 patients with consultation history
  - Consultations with mock transcripts, diagnoses, medications
"""
import sys, os, json
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from app.db.session import SessionLocal, engine, Base
from app.models.models import (
    User, Patient, Consultation, Diagnosis, Medication,
    UserRole, MedicationStatus, generate_patient_id
)
from app.core.security import get_password_hash

Base.metadata.create_all(bind=engine)
db = SessionLocal()


def clear_data():
    db.query(Medication).delete()
    db.query(Diagnosis).delete()
    db.query(Consultation).delete()
    db.query(User).delete()
    db.query(Patient).delete()
    db.commit()
    print("✓ Cleared existing seed data")


def seed_doctor():
    doctor = User(
        email="doctor@demo.com",
        password_hash=get_password_hash("Demo@1234"),
        role=UserRole.ROLE_DOCTOR,
    )
    db.add(doctor)
    db.flush()
    print(f"✓ Doctor created: doctor@demo.com / Demo@1234 (user_id={doctor.user_id})")
    return doctor


def seed_patient(name, phone, dob, gender, doctor_id, consult_data):
    pid = generate_patient_id()
    while db.query(Patient).filter(Patient.patient_id == pid).first():
        pid = generate_patient_id()

    patient = Patient(patient_id=pid, name=name, phone=phone, dob=dob, gender=gender)
    db.add(patient)
    db.flush()

    # Patient user account
    user = User(
        phone=phone,
        email=f"{name.lower().replace(' ', '.')}@demo.com",
        password_hash=get_password_hash("Patient@1234"),
        role=UserRole.ROLE_PATIENT,
        patient_id=pid,
    )
    db.add(user)
    db.flush()

    print(f"✓ Patient: {name} ({pid}) | email: {user.email} / Patient@1234")

    for i, c_data in enumerate(consult_data):
        soap_note = json.dumps({
            "subjective": c_data["subjective"],
            "objective": c_data["objective"],
            "assessment": c_data["assessment"],
            "plan": c_data["plan"],
        })

        consult = Consultation(
            patient_id=pid,
            doctor_id=doctor_id,
            transcript=c_data["transcript"],
            soap_note=soap_note,
            doctor_summary=c_data["doctor_summary"],
            patient_summary=c_data["patient_summary"],
            date=date.today() - timedelta(days=c_data["days_ago"]),
        )
        db.add(consult)
        db.flush()

        diagnosis = Diagnosis(
            consultation_id=consult.consultation_id,
            diagnosis_name=c_data["diagnosis"],
            severity=c_data["severity"],
        )
        db.add(diagnosis)

        for med in c_data["medications"]:
            db.add(Medication(
                consultation_id=consult.consultation_id,
                medicine_name=med["name"],
                dosage=med["dosage"],
                duration=med["duration"],
                status=MedicationStatus.active if i == len(consult_data) - 1 else MedicationStatus.completed,
            ))

        print(f"  └─ Consultation {consult.consultation_id}: {c_data['diagnosis']} ({c_data['days_ago']} days ago)")

    return patient


PATIENT_1_CONSULTS = [
    {
        "days_ago": 75,
        "transcript": "Patient reports persistent cough and low-grade fever for 5 days. Doctor notes mild bronchitis.",
        "subjective": "Persistent cough, low-grade fever (37.8°C), mild fatigue for 5 days.",
        "objective": "Temp 37.8°C. Mild expiratory wheeze on auscultation. No cyanosis.",
        "assessment": "Acute bronchitis, likely viral.",
        "plan": "Azithromycin 500mg OD x5 days, rest, fluids. Follow up in 7 days.",
        "diagnosis": "Acute Bronchitis",
        "severity": "mild",
        "doctor_summary": "Patient presented with viral acute bronchitis. Started on azithromycin empirically. Advised rest and hydration.",
        "patient_summary": "You have a chest infection causing your cough. Take the antibiotics as prescribed and rest well. Come back if you feel worse.",
        "medications": [
            {"name": "Azithromycin", "dosage": "500mg", "duration": "5 days"},
            {"name": "Paracetamol", "dosage": "500mg as needed", "duration": "5 days"},
        ],
    },
    {
        "days_ago": 40,
        "transcript": "Patient returns with recurring cough. Now productive, fever 38.5°C. Chest X-ray ordered.",
        "subjective": "Cough returned 2 weeks after previous visit. Now productive with yellow sputum. Fever 38.5°C.",
        "objective": "Temp 38.5°C. Coarse crackles bilateral lower lobes. SpO2 97%.",
        "assessment": "Community-acquired pneumonia, mild-moderate severity.",
        "plan": "Amoxicillin-Clavulanate 875/125mg BD x7 days. CXR follow-up in 2 weeks.",
        "diagnosis": "Community-Acquired Pneumonia",
        "severity": "moderate",
        "doctor_summary": "Recurrent respiratory illness progressing to CAP. Escalated to Augmentin. Chest X-ray ordered to confirm infiltrates.",
        "patient_summary": "Your chest infection has gotten stronger. We're giving you a stronger antibiotic. Please take the full course and come back for a chest X-ray.",
        "medications": [
            {"name": "Amoxicillin-Clavulanate", "dosage": "875/125mg", "duration": "7 days"},
            {"name": "Salbutamol Inhaler", "dosage": "2 puffs as needed", "duration": "7 days"},
        ],
    },
    {
        "days_ago": 10,
        "transcript": "Patient back with cough again, third visit. Shortness of breath on exertion. SpO2 95%.",
        "subjective": "Third episode of cough in 90 days. Shortness of breath on walking. Mild wheezing.",
        "objective": "SpO2 95% at rest. Diffuse wheeze. FEV1/FVC 68% (post-bronchodilator).",
        "assessment": "Possible underlying asthma or COPD. Recurrent bronchitis pattern.",
        "plan": "Start Budesonide/Formoterol inhaler. Refer to pulmonologist. PFTs ordered.",
        "diagnosis": "Recurrent Bronchospasm — Query Asthma",
        "severity": "moderate",
        "doctor_summary": "Third respiratory episode in 90 days suggesting underlying reactive airways disease. PFTs confirm mild obstructive pattern. Initiated ICS/LABA and pulmonology referral.",
        "patient_summary": "You've had breathing problems three times in 3 months, which suggests you may have asthma. We're starting an inhaler to help your lungs. We're also referring you to a lung specialist.",
        "medications": [
            {"name": "Budesonide/Formoterol", "dosage": "160/4.5mcg", "duration": "30 days"},
            {"name": "Montelukast", "dosage": "10mg OD", "duration": "30 days"},
        ],
    },
]

PATIENT_2_CONSULTS = [
    {
        "days_ago": 60,
        "transcript": "Patient reports severe headache, nausea, light sensitivity. No fever. Neuro exam normal.",
        "subjective": "Throbbing right-sided headache, nausea, photophobia. Duration 12 hours.",
        "objective": "BP 118/76. Neuro exam normal. No meningismus. No papilledema.",
        "assessment": "Migraine without aura.",
        "plan": "Sumatriptan 50mg PRN. Avoid triggers. Lifestyle modification counseling.",
        "diagnosis": "Migraine Without Aura",
        "severity": "moderate",
        "doctor_summary": "Classic unilateral migraine presentation without neurological deficits. Initiated triptans for acute management.",
        "patient_summary": "You have a migraine. We've given you medication to stop the headache quickly. Avoid bright lights and keep a headache diary.",
        "medications": [
            {"name": "Sumatriptan", "dosage": "50mg", "duration": "PRN"},
            {"name": "Metoclopramide", "dosage": "10mg", "duration": "PRN for nausea"},
        ],
    },
    {
        "days_ago": 20,
        "transcript": "Recurring headache, this time with visual aura (zigzag lines). Lasted 2 days.",
        "subjective": "Recurrent headache now with visual aura — zigzag lines before headache onset. Lasted 48 hours.",
        "objective": "BP 122/80. Visual fields intact. No focal neuro deficits.",
        "assessment": "Migraine with aura — increasing frequency warrants prophylaxis.",
        "plan": "Start Propranolol 40mg BD as prophylaxis. Continue Sumatriptan for acute attacks.",
        "diagnosis": "Migraine With Aura",
        "severity": "moderate",
        "doctor_summary": "Migraine evolving with aura and increasing frequency. Initiated beta-blocker prophylaxis to reduce attack burden.",
        "patient_summary": "Your migraines are happening more often and now include visual changes. We're starting a daily medicine to prevent them. Keep taking Sumatriptan when attacks happen.",
        "medications": [
            {"name": "Propranolol", "dosage": "40mg", "duration": "90 days"},
            {"name": "Sumatriptan", "dosage": "50mg", "duration": "PRN"},
        ],
    },
]


def main():
    print("\n🌱 Seeding healthcare demo database...\n")
    clear_data()

    doctor = seed_doctor()

    seed_patient(
        name="Rahul Mehta",
        phone="+919876543210",
        dob=date(1985, 4, 12),
        gender="male",
        doctor_id=doctor.user_id,
        consult_data=PATIENT_1_CONSULTS,
    )

    seed_patient(
        name="Priya Sharma",
        phone="+919876543211",
        dob=date(1992, 8, 25),
        gender="female",
        doctor_id=doctor.user_id,
        consult_data=PATIENT_2_CONSULTS,
    )

    db.commit()
    print("\n✅ Seed complete!\n")
    print("─" * 50)
    print("DOCTOR LOGIN")
    print("  Email:    doctor@demo.com")
    print("  Password: Demo@1234")
    print("\nPATIENT LOGIN")
    print("  Email:    rahul.mehta@demo.com / priya.sharma@demo.com")
    print("  Password: Patient@1234")
    print("─" * 50)
    print("\nRun the server: uvicorn app.main:app --reload")
    print("API Docs:       http://localhost:8000/docs\n")


if __name__ == "__main__":
    main()
