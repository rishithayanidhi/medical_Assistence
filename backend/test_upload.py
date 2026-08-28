"""
test_upload.py
--------------
Quick API test: uploads a sample prescription image to the local server
and prints the structured JSON response.

Usage:
    python test_upload.py
    python test_upload.py ../datasets/raw_prescriptions/eka_005.jpg
"""

import sys
import json
import os
import requests
import argparse
from dotenv import load_dotenv

# Load .env to get dynamic HOST and PORT defaults if available
load_dotenv()
DEFAULT_HOST = os.getenv("HOST", "127.0.0.1")
DEFAULT_PORT = os.getenv("PORT", "8000")
DEFAULT_URL = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/api/v1/documents/upload"

def test_document_upload(file_path: str, url: str):
    if not os.path.exists(file_path):
        print(f"[ERROR] File not found: '{file_path}'")
        return

    print(f"--> Uploading '{file_path}' to {url} ...")

    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "image/jpeg")}
        response = requests.post(url, files=files)

    print(f"Status: {response.status_code}\n")

    if response.status_code == 200:
        data = response.json()
        print("=== OCR Quality ===")
        print(f"  Quality : {data.get('ocr_quality')}")
        stats = data.get("ocr_stats", {})
        print(f"  Avg conf: {stats.get('avg')}  Min: {stats.get('min')}  Max: {stats.get('max')}")

        print("\n=== Patient Info ===")
        pi = data.get("patient_info", {})
        print(f"  Patient : {pi.get('patient_name') or 'Not detected'}")
        print(f"  Doctor  : {pi.get('doctor_name') or 'Not detected'}")
        print(f"  Date    : {pi.get('date') or 'Not detected'}")

        print("\n=== Extracted Medical Data ===")
        med = data.get("extracted_medical_data", {})
        print(f"  Medications         : {med.get('medications')}")
        print(f"  Unverified meds     : {med.get('unverified_medications')}")
        print(f"  Diagnoses/Symptoms  : {med.get('diagnoses_or_symptoms')}")
        print(f"  Dosages             : {med.get('dosages')}")
        print(f"  Frequencies         : {med.get('frequencies')}")

        print("\n=== Full JSON Response ===")
        print(json.dumps(data, indent=4))
    else:
        print("[ERROR]", response.text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test document upload API.")
    parser.add_argument("file", nargs="?", default="../datasets/raw_prescriptions/eka_000.jpg", help="Path to the image/PDF file.")
    parser.add_argument("--url", default=DEFAULT_URL, help="The full URL to the upload endpoint.")
    args = parser.parse_args()

    test_document_upload(args.file, args.url)