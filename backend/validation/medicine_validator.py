from typing import List

import json
import os

# ---------------------------------------------------------------------------
# Curated keyword set for basic medicine name verification.
# Loaded dynamically from drugs_keywords.json
# ---------------------------------------------------------------------------
_JSON_PATH = os.path.join(os.path.dirname(__file__), "drugs_keywords.json")

def load_keywords():
    try:
        with open(_JSON_PATH, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

_KNOWN_DRUG_KEYWORDS = load_keywords()

class MedicineValidator:
    """
    Validates a list of detected medication names against a known drug keyword set.

    Splits results into:
        - confirmed:   Likely valid drug names (keyword match found)
        - unverified:  Names that didn't match — may still be valid brand names
    """

    @staticmethod
    def validate(medications: List[str]) -> dict:
        """
        Validate detected medication names.

        Args:
            medications: List of medication strings from MedicineExtractor.

        Returns:
            dict with keys:
                - confirmed   (List[str]): Matched against known drug keywords
                - unverified  (List[str]): No keyword match found
        """
        confirmed: List[str] = []
        unverified: List[str] = []

        for med in medications:
            med_lower = med.lower()
            is_known = any(keyword in med_lower for keyword in _KNOWN_DRUG_KEYWORDS)
            if is_known:
                confirmed.append(med)
            else:
                unverified.append(med)

        return {"confirmed": confirmed, "unverified": unverified}
