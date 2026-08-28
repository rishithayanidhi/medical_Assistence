import os

# Disable PIR API and oneDNN for PaddleOCR stability on Windows CPU
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_use_onednn"] = "0"

from typing import List
from paddleocr import PaddleOCR

# Singleton OCR instance — loaded once, reused across requests
_ocr_instance = None


def get_ocr_engine() -> PaddleOCR:
    """Returns the shared PaddleOCR instance, initializing it on first call."""
    global _ocr_instance
    if _ocr_instance is None:
        _ocr_instance = PaddleOCR(use_angle_cls=False, lang="en", enable_mkldnn=False)
    return _ocr_instance


class OCREngine:
    """
    Runs PaddleOCR on a preprocessed image and returns raw extracted
    text lines along with their per-line confidence scores.
    """

    @staticmethod
    def run(image) -> dict:
        """
        Execute OCR on the given image array.

        Args:
            image: Preprocessed CV2 BGR image (numpy array, shape [H, W, 3])

        Returns:
            dict with keys:
                - lines (List[str]): OCR text lines above confidence threshold
                - confidence_scores (List[float]): Per-line confidence values
                - full_text (str): All lines joined into a single string
        """
        ocr = get_ocr_engine()
        ocr_results = ocr.ocr(image)

        extracted_lines: List[str] = []
        confidence_scores: List[float] = []

        if not ocr_results:
            return {"lines": [], "confidence_scores": [], "full_text": ""}

        for block in ocr_results:
            if block is None:
                continue

            # --- PaddleOCR 3.x / PaddleX dictionary output ---
            if isinstance(block, dict):
                rec_texts = block.get("rec_texts", [])
                rec_scores = block.get("rec_scores", [])
                for text, score in zip(rec_texts, rec_scores):
                    score = score if isinstance(score, (int, float)) else 1.0
                    if score > 0.4 and text and str(text).strip():
                        extracted_lines.append(str(text).strip())
                        confidence_scores.append(float(score))

            # --- Standard list / tuple output ---
            elif isinstance(block, (list, tuple)):
                for line in block:
                    if line is None:
                        continue
                    if isinstance(line, (list, tuple)) and len(line) >= 2:
                        text_info = line[1]
                        if isinstance(text_info, (list, tuple)) and len(text_info) >= 1:
                            text = str(text_info[0]).strip()
                            score = (
                                float(text_info[1])
                                if len(text_info) > 1 and isinstance(text_info[1], (int, float))
                                else 1.0
                            )
                            if score > 0.4 and text:
                                extracted_lines.append(text)
                                confidence_scores.append(score)
                        elif isinstance(text_info, str) and text_info.strip():
                            extracted_lines.append(text_info.strip())
                            confidence_scores.append(1.0)
                    elif isinstance(line, str) and line.strip():
                        extracted_lines.append(line.strip())
                        confidence_scores.append(1.0)

        return {
            "lines": extracted_lines,
            "confidence_scores": confidence_scores,
            "full_text": " ".join(extracted_lines),
        }
