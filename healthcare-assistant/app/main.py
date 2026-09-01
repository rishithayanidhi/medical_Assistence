import os
import traceback
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.utils.file_handler import save_uploaded_file
from app.services.ocr_service import extract_text_structured, extract_text
from app.services.simplify_service import simplify_text_detailed, simplify_text
from app.services.medical_extractor import extract_structured_medical_data

from app.services.simplify_service import (
    simplify_text_detailed, 
    simplify_text, 
    generate_voice_audio_sarvam
)

app = FastAPI(
    title="Healthcare Assistant API",
    description="Medical document OCR text extraction, JSON output formatting, and medical jargon simplification.",
    version="1.1.0"
)

# Enable CORS for frontend interactions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files directory setup
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(CURRENT_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class SimplifyRequest(BaseModel):
    text: str


@app.get("/")
def read_root():
    """Serves the interactive Web UI."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Healthcare Communication Assistant API is running. Access /docs for API documentation."}

@app.post("/extract-text")
async def extract_text_endpoint(file: UploadFile = File(...)):
  """Extracts raw text and filters pure medical JSON without auto-simplifying."""
  try:
    file_path = await save_uploaded_file(file)
    raw_text = extract_text(file_path)

    raw_lines = raw_text.split('\n')
    clinical_data = extract_structured_medical_data(raw_lines)

    return {
        "status": "success",
        "extracted_text": clinical_data["pure_medical_text"],
        "medical_data": clinical_data["medical_data"],
        "medical_lines": clinical_data["medical_lines"],
    }
  except Exception as e:
    print("\n--- ERROR TRACEBACK ---")
    traceback.print_exc()
    print("-----------------------\n")
    raise HTTPException(status_code=500, detail=str(e))


class SimplifyRequest(BaseModel):
    text: str
    medical_data: Optional[Dict[str, Any]] = None
    target_language: Optional[str] = "en"


class TTSRequest(BaseModel):
    text: str
    target_language: Optional[str] = "en"

@app.post("/text-to-speech")
def text_to_speech_endpoint(payload: TTSRequest):
    """Generates voice guidance audio in regional languages."""
    try:
        audio_base64 = generate_voice_audio_sarvam(payload.text, payload.target_language)
        return {
            "status": "success",
            "audio_base64": audio_base64,
            "language": payload.target_language
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice generation failed: {str(e)}")

@app.post("/simplify-text")
def simplify_medical_text(payload: SimplifyRequest):
    """Takes extracted medical data and translates the simplified text into regional languages via Sarvam AI."""
    try:
        data_to_simplify = payload.medical_data if payload.medical_data else payload.text
        result = simplify_text_detailed(data_to_simplify, target_language=payload.target_language)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simplification/Translation failed: {str(e)}")


@app.post("/process-document")
async def process_document(file: UploadFile = File(...)):
    """Full Pipeline: Upload -> OCR -> Administrative Noise Filter -> Simplification -> Pure JSON Output."""
    try:
        file_path = await save_uploaded_file(file)
        ocr_result = extract_text_structured(file_path)
        
        # Extract structured medical entities (Prescriptions, Vitals, Labs, Symptoms)
        raw_lines = ocr_result.get("raw_text", "").split('\n')
        clinical_extraction = extract_structured_medical_data(raw_lines)
        
        # Simplify pure medical text
        simplification_result = simplify_text_detailed(clinical_extraction["pure_medical_text"])

        return {
            "status": "success",
            "file_name": ocr_result["file_name"],
            "document_type": clinical_extraction["document_type"],
            "medical_data": clinical_extraction["medical_data"],
            "pure_medical_text": clinical_extraction["pure_medical_text"],
            "simplification": simplification_result
        }
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")