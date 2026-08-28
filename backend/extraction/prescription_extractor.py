from ocr.preprocessing import ImagePreprocessor
from ocr.ocr_engine import OCREngine
from extraction.patient_extractor import PatientExtractor
from extraction.medicine_extractor import MedicineExtractor
from validation.medicine_validator import MedicineValidator
from validation.confidence import ConfidenceScorer


class PrescriptionExtractor:
    """
    Top-level orchestrator that runs the full extraction pipeline:

        Image bytes
            → Preprocessing (CLAHE enhancement)
            → OCR (PaddleOCR raw text)
            → Patient Info extraction (regex)
            → Medicine/NER extraction (scisPaCy + regex)
            → Medicine validation (drug keyword check)
            → Confidence scoring (per-line average)
            → Final structured result dict
    """

    @staticmethod
    def process(file_bytes: bytes, filename: str) -> dict:
        """
        Run the full prescription extraction pipeline.

        Args:
            file_bytes: Raw bytes of the uploaded file (image or PDF).
            filename:   Original filename (used to detect PDF vs image).

        Returns:
            dict with keys:
                - raw_text         (str)
                - ocr_quality      (str)  "HIGH" | "MEDIUM" | "LOW"
                - ocr_stats        (dict) avg/min/max confidence
                - patient_info     (dict) patient_name, doctor_name, date
                - extracted_data   (dict) medications, diagnoses_or_symptoms,
                                          dosages, frequencies,
                                          unverified_medications
        """
        # 1. Preprocess image
        raw_img = ImagePreprocessor.read_file_as_cv2(file_bytes, filename)
        processed_img = ImagePreprocessor.enhance_for_ocr(raw_img)

        # 2. Run OCR
        ocr_result = OCREngine.run(processed_img)
        full_text = ocr_result["full_text"]
        confidence_scores = ocr_result["confidence_scores"]

        # 3. Score OCR quality
        quality = ConfidenceScorer.score(confidence_scores)
        stats = ConfidenceScorer.get_stats(confidence_scores)

        # 4. Extract patient metadata
        patient_info = PatientExtractor.extract(full_text)

        # 5. Extract medicines, diagnoses, dosages, frequencies
        medical_data = MedicineExtractor.extract(full_text)

        # 6. Validate detected medication names
        validated = MedicineValidator.validate(medical_data["medications"])
        medical_data["medications"] = validated["confirmed"]
        medical_data["unverified_medications"] = validated["unverified"]

        return {
            "raw_text": full_text,
            "ocr_quality": quality,
            "ocr_stats": stats,
            "patient_info": patient_info,
            "extracted_data": medical_data,
        }
