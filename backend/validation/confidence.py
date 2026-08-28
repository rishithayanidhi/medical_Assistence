from typing import List


class ConfidenceScorer:
    """
    Computes an overall OCR quality rating from per-line PaddleOCR confidence scores.

    Quality levels:
        HIGH   — avg confidence ≥ 0.80  (clear, well-scanned document)
        MEDIUM — avg confidence ≥ 0.60  (readable but some noise)
        LOW    — avg confidence < 0.60  (blurry / low-resolution scan)
    """

    HIGH_THRESHOLD: float = 0.80
    MEDIUM_THRESHOLD: float = 0.60

    @staticmethod
    def score(confidence_scores: List[float]) -> str:
        """
        Return a quality label from a list of per-line confidence values.

        Args:
            confidence_scores: List of floats in [0.0, 1.0] from OCREngine.

        Returns:
            "HIGH" | "MEDIUM" | "LOW"
        """
        if not confidence_scores:
            return "LOW"
        avg = sum(confidence_scores) / len(confidence_scores)
        if avg >= ConfidenceScorer.HIGH_THRESHOLD:
            return "HIGH"
        elif avg >= ConfidenceScorer.MEDIUM_THRESHOLD:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def get_stats(confidence_scores: List[float]) -> dict:
        """
        Return detailed confidence statistics.

        Args:
            confidence_scores: List of floats from OCREngine.

        Returns:
            dict with keys: avg, min, max (rounded to 3 dp), quality (str)
        """
        if not confidence_scores:
            return {"avg": 0.0, "min": 0.0, "max": 0.0, "quality": "LOW"}

        avg = sum(confidence_scores) / len(confidence_scores)
        return {
            "avg": round(avg, 3),
            "min": round(min(confidence_scores), 3),
            "max": round(max(confidence_scores), 3),
            "quality": ConfidenceScorer.score(confidence_scores),
        }
