import re

import spacy

# Load scisPaCy biomedical NER model — gracefully degrades if not installed
try:
    _nlp_ner = spacy.load("en_ner_bc5cdr_md")
except OSError:
    _nlp_ner = None


class MedicineExtractor:
    """
    Extracts medical entities from OCR text using two complementary methods:

    1. scisPaCy NER (en_ner_bc5cdr_md):
       - CHEMICAL label → medications
       - DISEASE label  → diagnoses / symptoms

    2. Regex patterns:
       - Dosage strengths (e.g., 500 mg, 10 ml, 2 tablets)
       - Frequency instructions (e.g., 1-0-1, twice a day, after food)
    """

    _DOSAGE_PATTERN = r"(\d+\s*(?:mg|g|ml|mcg|tablet|tablets|capsule|capsules|drops|units))"
    _FREQUENCY_PATTERN = (
        r"\b("
        r"once|twice|thrice"
        r"|\d+\s*times?\s*(?:a|per)\s*day"
        r"|1-0-1|1-1-1|0-0-1|1-0-0|0-1-0|1-1-0|0-1-1"
        r"|after\s*food|before\s*food|after\s*meal|before\s*meal"
        r"|empty\s*stomach|at\s*bedtime|with\s*food"
        r")\b"
    )

    @staticmethod
    def extract(text: str) -> dict:
        """
        Extract medications, diagnoses, dosages, and frequencies from text.

        Args:
            text: Full OCR output string.

        Returns:
            dict with keys:
                - medications (List[str])
                - diagnoses_or_symptoms (List[str])
                - dosages (List[str])
                - frequencies (List[str])
        """
        medications = []
        diseases = []

        # --- scisPaCy NER extraction ---
        if _nlp_ner and text.strip():
            doc = _nlp_ner(text)
            for ent in doc.ents:
                if ent.label_ == "CHEMICAL":
                    medications.append(ent.text)
                elif ent.label_ == "DISEASE":
                    diseases.append(ent.text)

        # --- Regex extraction ---
        dosages = re.findall(MedicineExtractor._DOSAGE_PATTERN, text, re.IGNORECASE)
        frequencies = re.findall(MedicineExtractor._FREQUENCY_PATTERN, text, re.IGNORECASE)

        return {
            "medications": list(set(medications)),
            "diagnoses_or_symptoms": list(set(diseases)),
            "dosages": list(set(dosages)),
            "frequencies": list(set(frequencies)),
        }
