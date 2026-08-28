import cv2
import numpy as np
from PIL import Image
import pymupdf  # PyMuPDF


class ImagePreprocessor:
    """Handles file decoding (PDF/image) and OpenCV enhancement for OCR."""

    @staticmethod
    def read_file_as_cv2(file_bytes: bytes, filename: str) -> np.ndarray:
        """Convert uploaded file bytes (PDF or image) into a CV2 BGR image array."""
        if filename.lower().endswith(".pdf"):
            # Render first page of PDF at 300 DPI
            doc = pymupdf.open(stream=file_bytes, filetype="pdf")
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        else:
            # Decode PNG, JPG, JPEG from raw bytes
            nparr = np.frombuffer(file_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError(
                    f"Could not decode image '{filename}'. "
                    "File may be corrupted or unsupported."
                )
            return img

    @staticmethod
    def enhance_for_ocr(img: np.ndarray) -> np.ndarray:
        """
        Applies CLAHE contrast enhancement to boost text legibility.
        Returns a 3-channel BGR image as required by PaddleOCR.
        """
        if img is None or img.size == 0:
            raise ValueError("Input image for OCR enhancement is empty or None.")

        # Ensure 3-channel input
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply CLAHE: sharpens low-contrast prescription text
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced_gray = clahe.apply(gray)

        # Convert back to BGR (PaddleOCR requires [H, W, 3])
        return cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2BGR)
