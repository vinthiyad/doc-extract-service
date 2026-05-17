"""
OCR extraction for scanned documents and images.
Uses Tesseract via pytesseract with optional OpenCV preprocessing.
"""

import os
from typing import List
import cv2
import numpy as np
import pytesseract
from PIL import Image


def extract_from_image(filepath: str, warnings: List[str]) -> str:
    """
    Run Tesseract OCR on an image or scanned PDF page.
    Applies preprocessing: grayscale, adaptive threshold, deskew, denoise.
    Falls back to raw OCR if preprocessing fails.
    """
    if filepath.lower().endswith(".pdf"):
        return _ocr_pdf_with_tesseract(filepath, warnings)

    return _ocr_image(filepath, warnings)


def _ocr_image(filepath: str, warnings: List[str]) -> str:
    """Run Tesseract on a single image file."""
    try:
        img = cv2.imread(filepath)
        if img is None:
            warnings.append("Could not read image — returning empty text.")
            return ""

        processed = _preprocess_image(img)
        custom_config = r"--oem 3 --psm 6 -l eng"
        text = pytesseract.image_to_string(processed, config=custom_config)
        return text.strip()

    except Exception as e:
        warnings.append(f"Preprocessing failed ({e}). Falling back to raw OCR.")
        try:
            img = Image.open(filepath)
            text = pytesseract.image_to_string(img)
            return text.strip()
        except Exception as e2:
            warnings.append(f"Tesseract OCR failed: {e2}")
            return ""


def _ocr_pdf_with_tesseract(filepath: str, warnings: List[str]) -> str:
    """Convert each page of a PDF to an image and OCR it."""
    import fitz  # PyMuPDF
    try:
        doc = fitz.open(filepath)
        all_text = []
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            tmp_img = f"{filepath}_page_{i}.png"
            img.save(tmp_img, "PNG")
            page_text = _ocr_image(tmp_img, warnings)
            all_text.append(page_text)
            os.unlink(tmp_img)
        doc.close()
        return "\n".join(all_text)
    except Exception as e:
        warnings.append(f"PDF OCR failed: {e}")
        return ""


def _preprocess_image(img: np.ndarray) -> np.ndarray:
    """
    Apply OpenCV preprocessing to improve OCR accuracy.
    Steps: grayscale → adaptive threshold → deskew → denoise.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2
    )

    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        if abs(angle) > 0.5:
            (h, w) = thresh.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            thresh = cv2.warpAffine(
                thresh, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
            )

    denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)
    return denoised