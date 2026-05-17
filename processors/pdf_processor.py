"""
PDF text extraction for machine-generated (native) PDFs.
Uses pdfplumber as the primary engine; falls back to PyMuPDF.
"""

from typing import List
import pdfplumber
import fitz  # PyMuPDF


def extract_from_native_pdf(filepath: str, warnings: List[str]) -> str:
    """
    Extract all text from a native PDF.
    Uses pdfplumber first (better table handling),
    falls back to PyMuPDF if pdfplumber yields too little text.
    """
    text = ""

    # --- Primary: pdfplumber ---
    try:
        with pdfplumber.open(filepath) as pdf:
            pages_text = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pages_text.append(page_text)
            text = "\n".join(pages_text)
    except Exception as e:
        warnings.append(f"pdfplumber extraction error: {e}")

    # --- Fallback: PyMuPDF ---
    if len(text.strip()) < 100:
        try:
            doc = fitz.open(filepath)
            pages_text = []
            for page in doc:
                pages_text.append(page.get_text())
            text = "\n".join(pages_text)
            doc.close()
        except Exception as e:
            warnings.append(f"PyMuPDF fallback error: {e}")

    return text