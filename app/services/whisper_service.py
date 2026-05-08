import os
from typing import Optional


async def transcribe_audio(audio_path: str) -> Optional[str]:
    """
    Transcribe audio using OpenAI Whisper (local model).
    Falls back to a mock transcript if Whisper is unavailable (e.g., no GPU).
    """
    if not os.path.exists(audio_path):
        return None

    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        return result.get("text", "").strip()
    except ImportError:
        print("[Whisper] whisper not installed. Using mock transcript.")
        return _mock_transcript()
    except Exception as e:
        print(f"[Whisper] Transcription failed: {e}. Using mock transcript.")
        return _mock_transcript()


def _mock_transcript() -> str:
    """Fallback mock transcript for demo/testing without GPU."""
    return (
        "Doctor: Good morning. What brings you in today? "
        "Patient: I've been having a persistent cough for about two weeks now, along with some fever and fatigue. "
        "Doctor: Any shortness of breath or chest pain? "
        "Patient: A little shortness of breath but no chest pain. "
        "Doctor: I see. Let me examine you. Your temperature is 38.2 degrees. Lungs have some mild crackles. "
        "Based on your symptoms and examination, this looks like a mild respiratory infection, possibly bronchitis. "
        "I'm going to prescribe Amoxicillin 500mg three times a day for 7 days, and Paracetamol 500mg as needed for fever. "
        "Please rest, drink plenty of fluids, and come back in 10 days if you don't improve. "
        "Patient: Thank you, doctor."
    )
