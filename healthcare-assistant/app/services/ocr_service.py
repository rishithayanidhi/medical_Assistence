import os
import easyocr
from PIL import Image
from PyPDF2 import PdfReader
from pdf2image import convert_from_path  # Requires: pip install pdf2image

# Initialize EasyOCR reader for English (downloads lightweight model once)
reader = easyocr.Reader(['en'], gpu=False)

# Fine, adjacent characters (a bare digit next to a thin dash/em-dash, as
# in dose codes like "0 — 0 — 1") are exactly what gets merged or dropped
# when the source image is low-resolution. Rendering PDFs at a higher DPI
# and upscaling small images gives EasyOCR more pixels per character to
# work with, which is the actual fix — no downstream code can recover a
# character the OCR step never detected.
PDF_RENDER_DPI = 300
MIN_IMAGE_WIDTH = 1600  # upscale anything narrower than this before OCR


def _prepare_image_for_ocr(image_path: str) -> str:
    """
    Upscale small/low-resolution images in place before OCR. Returns the
    same path (the file is overwritten only if it needed upscaling).
    Never alters images that are already large enough — avoids
    unnecessary recompression of already-good input.
    """
    try:
        with Image.open(image_path) as img:
            if img.width < MIN_IMAGE_WIDTH:
                scale = MIN_IMAGE_WIDTH / img.width
                new_size = (int(img.width * scale), int(img.height * scale))
                upscaled = img.convert("RGB").resize(new_size, Image.LANCZOS)
                upscaled.save(image_path)
    except Exception as e:
        # If preprocessing fails for any reason, fall through and let
        # EasyOCR try the original file rather than losing the page.
        print(f"Image preprocessing skipped for {os.path.basename(image_path)}: {e}")
    return image_path


def extract_text_from_image(image_path: str) -> str:
    """Dynamically extracts raw OCR text using EasyOCR."""
    try:
        _prepare_image_for_ocr(image_path)
        results = reader.readtext(
            image_path,
            detail=0,
            # Slightly relaxed thresholds help detect thin/faint
            # characters (dashes, decimal points) on scanned documents
            # without materially increasing false positives.
            contrast_ths=0.05,
            adjust_contrast=0.7,
        )
        extracted_text = "\n".join(results)
        return extracted_text.strip()
    except Exception as e:
        print(f"EasyOCR Error: {e}")
        return ""


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts digital text first; falls back to EasyOCR if the PDF is scanned."""
    # 1. Try extracting native digital text first (Fastest)
    pdf_reader = PdfReader(pdf_path)
    extracted_text = []
    for page in pdf_reader.pages:
        text = page.extract_text()
        if text:
            extracted_text.append(text)

    digital_text = "\n".join(extracted_text).strip()

    # 2. If it's a scanned PDF, digital_text will be empty. Fallback to OCR.
    if not digital_text:
        print(f"No digital text found in {os.path.basename(pdf_path)}. Running OCR conversion...")
        try:
            # Convert PDF pages to PIL Images at a high enough DPI that
            # thin characters (dashes, small digits in dose codes) don't
            # get merged or dropped during OCR.
            pages = convert_from_path(pdf_path, dpi=PDF_RENDER_DPI)
            ocr_text_list = []

            for i, page in enumerate(pages):
                # Save page temporarily to read via EasyOCR
                temp_image_path = f"temp_page_{i}.png"
                page.save(temp_image_path, 'PNG')

                # Perform OCR
                page_text = extract_text_from_image(temp_image_path)
                ocr_text_list.append(page_text)

                # Clean up temp image
                os.remove(temp_image_path)

            return "\n".join(ocr_text_list).strip()
        except Exception as e:
            print(f"PDF OCR Error: {e}")
            return ""

    return digital_text


def extract_text(file_path: str) -> str:
    file_ext = file_path.split(".")[-1].lower()
    if file_ext == "pdf":
        return extract_text_from_pdf(file_path).strip()
    return extract_text_from_image(file_path).strip()


def extract_text_structured(file_path: str) -> dict:
    raw_text = extract_text(file_path)
    file_name = os.path.basename(file_path)
    return {
        "file_name": file_name,
        "raw_text": raw_text
    }