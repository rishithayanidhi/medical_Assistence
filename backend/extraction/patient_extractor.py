import re
from typing import Optional


class PatientExtractor:
    """
    Extracts patient-level metadata from raw OCR text using regex patterns.

    Detects:
        - Patient name
        - Doctor / physician name
        - Prescription date
    """

    # Ordered by specificity: most explicit patterns first
    _NAME_PATTERNS = [
        r'(?:Patient\s*Name|Patient|Pt\.?)\s*[:\-]?\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3})',
        r'(?:Mr\.|Mrs\.|Ms\.)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})',
    ]

    _DOCTOR_PATTERNS = [
        r'(?:Dr\.?|Doctor)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})',
        r'(?:Physician|Prescribed\s+by|Consultant)\s*[:\-]?\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})',
    ]

    _DATE_PATTERNS = [
        r'\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\b',
        r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{2,4})\b',
        r'\bDate\s*[:\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\b',
    ]

    @staticmethod
    def _find_first(text: str, patterns: list) -> Optional[str]:
        """Return the first regex match from a list of patterns, or None."""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    @staticmethod
    def extract(text: str) -> dict:
        """
        Extract patient metadata from raw OCR text.

        Args:
            text: Full OCR output string.

        Returns:
            dict with keys: patient_name, doctor_name, date (all str | None)
        """
        return {
            "patient_name": PatientExtractor._find_first(text, PatientExtractor._NAME_PATTERNS),
            "doctor_name": PatientExtractor._find_first(text, PatientExtractor._DOCTOR_PATTERNS),
            "date": PatientExtractor._find_first(text, PatientExtractor._DATE_PATTERNS),
        }
