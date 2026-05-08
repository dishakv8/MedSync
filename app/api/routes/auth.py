import random
import string
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import User, UserRole, OTPStore, Patient, generate_patient_id
from app.schemas.schemas import RegisterRequest, LoginRequest, OTPSendRequest, OTPVerifyRequest
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.responses import success_response, error_response
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    # Validate inputs
    if not payload.email and not payload.phone:
        return error_response("Email or phone required")

    if payload.email and db.query(User).filter(User.email == payload.email).first():
        return error_response("Email already registered")

    if payload.phone and db.query(User).filter(User.phone == payload.phone).first():
        return error_response("Phone already registered")

    patient_id = None

    # If registering as patient, auto-create a patient record
    if payload.role == UserRole.ROLE_PATIENT:
        if not payload.name:
            return error_response("Name is required for patient registration")
        # Generate unique patient_id
        pid = generate_patient_id()
        while db.query(Patient).filter(Patient.patient_id == pid).first():
            pid = generate_patient_id()
        patient = Patient(patient_id=pid, name=payload.name, phone=payload.phone)
        db.add(patient)
        db.flush()
        patient_id = pid

    user = User(
        email=payload.email,
        phone=payload.phone,
        password_hash=get_password_hash(payload.password),
        role=payload.role,
        patient_id=patient_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return success_response(
        data={"user_id": user.user_id, "role": user.role, "patient_id": patient_id},
        message="Registered successfully",
        status_code=201,
    )


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = None
    if payload.email:
        user = db.query(User).filter(User.email == payload.email).first()
    elif payload.phone:
        user = db.query(User).filter(User.phone == payload.phone).first()

    if not user or not user.password_hash:
        return error_response("Invalid credentials", 401)

    if not verify_password(payload.password, user.password_hash):
        return error_response("Invalid credentials", 401)

    token = create_access_token({"sub": str(user.user_id), "role": user.role})
    return success_response(
        data={"access_token": token, "token_type": "bearer", "role": user.role, "user_id": user.user_id},
        message="Login successful",
    )


@router.post("/otp/send")
def send_otp(payload: OTPSendRequest, db: Session = Depends(get_db)):
    otp_code = "".join(random.choices(string.digits, k=6))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

    # Invalidate old OTPs for this phone
    db.query(OTPStore).filter(OTPStore.phone == payload.phone, OTPStore.used == False).update({"used": True})

    otp_entry = OTPStore(phone=payload.phone, otp_code=otp_code, expires_at=expires_at)
    db.add(otp_entry)
    db.commit()

    # In prod: send via Twilio/SMS. In mock mode, return in response.
    data = {"message": "OTP sent"}
    if settings.USE_MOCK_OTP:
        data["otp"] = otp_code  # For hackathon demo only

    return success_response(data=data, message="OTP sent successfully")


@router.post("/otp/verify")
def verify_otp(payload: OTPVerifyRequest, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    otp_entry = (
        db.query(OTPStore)
        .filter(
            OTPStore.phone == payload.phone,
            OTPStore.otp_code == payload.otp,
            OTPStore.used == False,
            OTPStore.expires_at > now,
        )
        .first()
    )

    if not otp_entry:
        return error_response("Invalid or expired OTP", 401)

    otp_entry.used = True
    db.commit()

    user = db.query(User).filter(User.phone == payload.phone).first()
    if not user:
        return error_response("No account linked to this phone. Please register first.", 404)

    token = create_access_token({"sub": str(user.user_id), "role": user.role})
    return success_response(
        data={"access_token": token, "token_type": "bearer", "role": user.role, "user_id": user.user_id},
        message="OTP verified, login successful",
    )
