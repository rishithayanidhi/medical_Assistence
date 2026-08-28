"""
utils/text_cleaning.py
----------------------
Shared text normalization helpers used across the extraction pipeline.

Functions:
    clean_ocr_text(text)       — Remove OCR noise and normalize whitespace
    normalize_drug_name(name)  — Standardize drug name casing and units
    remove_special_chars(text) — Strip non-alphanumeric chars (keep spaces)
    split_into_sentences(text) — Split raw OCR blob into logical lines
"""

import re
import unicodedata


def clean_ocr_text(text: str) -> str:
    """
    Normalize raw OCR output:
      - Normalize Unicode characters (e.g., replace curly quotes)
      - Collapse multiple whitespace into single spaces
      - Remove stray control characters
      - Strip leading/trailing whitespace

    Args:
        text: Raw string from PaddleOCR.

    Returns:
        Cleaned string.
    """
    if not text:
        return ""

    # Normalize unicode (NFKC: compatible decomposition + canonical composition)
    text = unicodedata.normalize("NFKC", text)

    # Remove control characters (except newline/tab which may be meaningful)
    text = re.sub(r"[^\S\n\t ]+", " ", text)

    # Collapse multiple whitespace into one space
    text = re.sub(r"[ \t]+", " ", text)

    # Remove leading/trailing whitespace per line
    lines = [line.strip() for line in text.splitlines()]
    text = " ".join(line for line in lines if line)

    return text.strip()


def normalize_drug_name(name: str) -> str:
    """
    Standardize a drug name for display or comparison:
      - Title-case the name
      - Preserve dosage units in their correct case (mg, ml, mcg)
      - Strip excess whitespace

    Args:
        name: Raw drug name string (e.g., "PARACETAMOL 500MG TAB")

    Returns:
        Normalized string (e.g., "Paracetamol 500mg Tab")

    Examples:
        >>> normalize_drug_name("AMOXICILLIN 250MG CAPSULE")
        'Amoxicillin 250mg Capsule'
    """
    if not name:
        return ""

    # Title-case the whole string first
    normalized = name.strip().title()

    # Fix unit casing: title-case converts "Mg" → force back to "mg"
    unit_fixes = {
        r"\bMg\b": "mg",
        r"\bMl\b": "ml",
        r"\bMcg\b": "mcg",
        r"\bG\b": "g",
        r"\bIu\b": "IU",
    }
    for pattern, replacement in unit_fixes.items():
        normalized = re.sub(pattern, replacement, normalized)

    return normalized


def remove_special_chars(text: str) -> str:
    """
    Remove non-alphanumeric characters while preserving spaces.
    Useful for cleaning text before regex matching.

    Args:
        text: Input string.

    Returns:
        String with only alphanumeric characters and spaces.
    """
    return re.sub(r"[^a-zA-Z0-9\s]", " ", text)


def split_into_sentences(text: str) -> list:
    """
    Split a raw OCR text blob into logical lines/sentences.
    Splits on newlines, multiple spaces, and common sentence delimiters.

    Args:
        text: Full OCR output string.

    Returns:
        List of non-empty string segments.
    """
    # Split on newlines or sequences of 3+ spaces (common in OCR output)
    parts = re.split(r"\n|(?:  {2,})", text)
    return [p.strip() for p in parts if p.strip()]
