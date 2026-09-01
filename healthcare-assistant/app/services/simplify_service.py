import os
import re
import requests
from typing import Dict, Any, List

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "sk_5r5rsub6_IKylwLaYyLj0pIbW8P2woQeO")
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_TRANSLATE_URL = "https://api.sarvam.ai/translate"
LANGUAGE_CODES = {
    "ta": "ta-IN", "hi": "hi-IN", "te": "te-IN", "kn": "kn-IN",
    "ml": "ml-IN", "mr": "mr-IN", "bn": "bn-IN", "gu": "gu-IN",
    "or": "or-IN", "en": "en-IN"
}

def translate_text_sarvam(text: str, target_lang_code: str) -> str:
    if not text.strip() or target_lang_code not in LANGUAGE_CODES or target_lang_code == "en":
        return text

    target_sarvam_code = LANGUAGE_CODES[target_lang_code]
    headers = {
        "Content-Type": "application/json",
        "api-subscription-key": SARVAM_API_KEY
    }
    payload = {
        "input": text,
        "source_language_code": "en-IN",
        "target_language_code": target_sarvam_code,
        "speaker_gender": "Female",
        "mode": "formal",
        "enable_preprocessing": True
    }

    try:
        response = requests.post(SARVAM_TRANSLATE_URL, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("translated_text", text)
    except Exception as e:
        print(f"Sarvam Translation Exception: {e}")

    return text


def convert_to_pure_tamil_voice_script(medical_data: Dict[str, Any]) -> str:
    """Creates a 100% Pure Spoken Tamil Script for Sarvam AI Audio Engine."""
    prescriptions = medical_data.get("prescriptions", [])
    problems = medical_data.get("health_problem", [])

    tamil_numbers = ["ஒன்று", "இரண்டு", "மூன்று", "நான்கு", "ஐந்து"]
    
    prob_str = ", ".join(problems) if problems else "பிபோலார் மூட் டிஸார்டர்"

    sentences = []
    sentences.append(f"நோயாளிக்கான மருத்துவ வழிகாட்டி. உங்களின் உடல்நலக் கோளாறு: {prob_str}.")
    
    if prescriptions:
        count_ta = tamil_numbers[len(prescriptions)-1] if len(prescriptions) <= 5 else str(len(prescriptions))
        sentences.append(f"உங்களுக்கு மொத்தம் {count_ta} மருந்துகள் பரிந்துரைக்கப்பட்டுள்ளன.")

        for idx, p in enumerate(prescriptions):
            num_ta = tamil_numbers[idx] if idx < len(tamil_numbers) else str(idx + 1)
            name = p.get('medicine_name', 'மருந்து')
            dosage = p.get('dosage', '').replace("MG", "மில்லிகிராம்").replace("mg", "மில்லிகிராம்")
            timing = p.get('timing', 'இரவு உணவுக்குப் பிறகு')
            freq = p.get('frequency', 'தினமும் ஒரு வேளை')

            # Clean English timing words to spoken Tamil
            if "Dinner" in timing or "Night" in freq:
                timing_ta = "இரவு உணவுக்குப் பிறகு சாப்பிடவும்"
            elif "Breakfast" in timing or "Morning" in freq:
                timing_ta = "காலை உணவுக்குப் பிறகு சாப்பிடவும்"
            else:
                timing_ta = "உணவுக்குப் பிறகு சாப்பிடவும்"

            sentences.append(f"மருந்து {num_ta}: {name}, அளவு {dosage}. {timing_ta}.")
    else:
        sentences.append("மருந்து சீட்டில் உள்ள அறிவுரைப்படி மருந்துகளை உட்கொள்ளவும்.")

    return " ".join(sentences)


def generate_patient_summary_data(medical_data: Dict[str, Any]) -> Dict[str, Any]:
    prescriptions = medical_data.get("prescriptions", [])
    problems = medical_data.get("health_problem", [])

    display_lines = []
    prob_str = ", ".join(problems) if problems else "Bipolar Mood Disorder"
    display_lines.append(f"Health Condition: {prob_str}")

    if prescriptions:
        display_lines.append(f"Total Medicines Prescribed: {len(prescriptions)}")
        for idx, p in enumerate(prescriptions, 1):
            name = p.get('medicine_name', 'Medication')
            dosage = p.get('dosage', 'As prescribed')
            freq = p.get('frequency', 'As directed')
            timing = p.get('timing', 'After Dinner')

            display_lines.append(f"Medicine {idx}: Take {name} ({dosage}) - Schedule: {freq} - Timing: {timing}")
    else:
        display_lines.append("Medicine: Follow doctor instructions on prescription slip.")

    return {
        "display_lines": display_lines
    }


def simplify_text_detailed(payload: Any, target_language: str = "en") -> Dict[str, Any]:
    if isinstance(payload, dict):
        med_data = payload.get("medical_data", payload)
        summary_data = generate_patient_summary_data(med_data)
    else:
        med_data = {}
        summary_data = {"display_lines": [str(payload)]}

    translated_lines = []
    for line in summary_data["display_lines"]:
        if target_language != "en":
            translated_lines.append(translate_text_sarvam(line, target_language))
        else:
            translated_lines.append(line)

    # Build Dedicated Natural Spoken Script for Audio Button
    if target_language == "ta":
        voice_script_final = convert_to_pure_tamil_voice_script(med_data)
    else:
        voice_script_final = " ".join(summary_data["display_lines"]).replace("|", ".")

    return {
        "status": "success",
        "simplified_text": "\n".join(translated_lines),
        "simplified_lines": translated_lines,
        "voice_script": voice_script_final,
        "language": target_language
    }


def simplify_text(raw_text: str) -> str:
    return raw_text.strip() if raw_text else ""


def generate_voice_audio_sarvam(text: str, target_lang_code: str) -> str:
    if not text.strip():
        return ""

    target_sarvam_code = LANGUAGE_CODES.get(target_lang_code, "en-IN")
    headers = {
        "Content-Type": "application/json",
        "api-subscription-key": SARVAM_API_KEY
    }

    payload = {
        "inputs": [text[:500]],
        "target_language_code": target_sarvam_code,
        "speaker": "meera",
        "pitch": 0,
        "pace": 0.95,
        "loudness": 1.5,
        "speech_sample_rate": 8000,
        "enable_preprocessing": True,
        "model": "bulbul:v1"
    }

    try:
        response = requests.post(SARVAM_TTS_URL, json=payload, headers=headers, timeout=12)
        if response.status_code == 200:
            audios = response.json().get("audios", [])
            if audios:
                return audios[0]
    except Exception as e:
        print(f"Sarvam TTS Exception: {e}")

    return ""