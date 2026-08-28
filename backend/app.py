import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Disable PIR API and oneDNN for PaddleOCR stability on Windows CPU
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_use_onednn"] = "0"

from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional

from extraction.prescription_extractor import PrescriptionExtractor

# ---------------------------------------------------------------------------
# Pydantic response schemas
# ---------------------------------------------------------------------------

class PatientInfo(BaseModel):
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    date: Optional[str] = None


class OCRStats(BaseModel):
    avg: float
    min: float
    max: float
    quality: str


class ExtractedMedicalData(BaseModel):
    medications: List[str]
    unverified_medications: List[str]
    diagnoses_or_symptoms: List[str]
    dosages: List[str]
    frequencies: List[str]


class PrescriptionResponse(BaseModel):
    filename: str
    status: str
    raw_text: str
    ocr_quality: str
    ocr_stats: OCRStats
    patient_info: PatientInfo
    extracted_medical_data: ExtractedMedicalData


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="MediPulse AI — Healthcare Communication Assistant",
    description=(
        "Backend API for prescription scanning, OCR, medical entity extraction, "
        "dosage scheduling, and voice guidance."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Allowed upload file extensions
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}

# Path to sample prescription dataset
_DEFAULT_DATASET = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "datasets", "raw_prescriptions"))
DATASET_DIR = os.getenv("DATASET_DIR", _DEFAULT_DATASET)


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.post(
    "/api/v1/documents/upload",
    response_model=PrescriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload a scanned prescription or lab report image/PDF for analysis.",
    tags=["Documents & OCR"],
)
async def upload_document(file: UploadFile = File(...)):
    """
    Accepts PNG, JPG, JPEG, or PDF files.

    Runs the full extraction pipeline:
      preprocessing → OCR → patient info → medicine NER → validation → confidence scoring

    Returns structured JSON with medications, diagnoses, dosages, frequencies,
    patient metadata, and OCR quality metrics.
    """
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. Allowed: {ALLOWED_EXTENSIONS}",
        )

    try:
        file_bytes = await file.read()
        result = PrescriptionExtractor.process(file_bytes, filename)

        return PrescriptionResponse(
            filename=filename,
            status="SUCCESS",
            raw_text=result["raw_text"],
            ocr_quality=result["ocr_quality"],
            ocr_stats=OCRStats(**result["ocr_stats"]),
            patient_info=PatientInfo(**result["patient_info"]),
            extracted_medical_data=ExtractedMedicalData(
                medications=result["extracted_data"]["medications"],
                unverified_medications=result["extracted_data"]["unverified_medications"],
                diagnoses_or_symptoms=result["extracted_data"]["diagnoses_or_symptoms"],
                dosages=result["extracted_data"]["dosages"],
                frequencies=result["extracted_data"]["frequencies"],
            ),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Processing error: {str(e)}",
        )


@app.get(
    "/api/v1/samples",
    summary="List available sample prescription images from the dataset.",
    tags=["Samples"],
)
def list_samples():
    """Returns up to 12 sample prescription filenames for quick UI testing."""
    if not os.path.exists(DATASET_DIR):
        return {"samples": []}
    files = [
        f for f in os.listdir(DATASET_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ][:12]
    return {"samples": files}


@app.get(
    "/api/v1/samples/{filename}",
    summary="Serve a sample prescription image file.",
    tags=["Samples"],
)
def get_sample_file(filename: str):
    """Serves a specific sample image from the dataset directory."""
    safe_name = os.path.basename(filename)
    file_path = os.path.join(DATASET_DIR, safe_name)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Sample file not found.")


# ---------------------------------------------------------------------------
# Serve Web UI (index.html)
# ---------------------------------------------------------------------------
_INDEX_PATH = os.path.join(os.path.dirname(__file__), "index.html")


@app.get("/", response_class=FileResponse, include_in_schema=False)
def serve_ui():
    if os.path.exists(_INDEX_PATH):
        return FileResponse(_INDEX_PATH)
    return JSONResponse(content={"status": "online", "version": "2.0.0"})


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host=host, port=port, reload=True)
