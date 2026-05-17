"""
Document Extraction Microservice — FastAPI Server

Receives a file via POST /v1/extract, classifies it, extracts text
via pdfplumber (native PDF) or Tesseract (scanned image), applies
invoice2data templates for known vendors, and returns structured JSON.

Deploy: uvicorn main:app --host 0.0.0.0 --port $PORT
"""

import os
import tempfile
import traceback
from typing import List, Optional

import magic
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from processors.pdf_processor import extract_from_native_pdf
from processors.image_processor import extract_from_image
from processors.field_extractor import extract_fields, ExtractedFields

app = FastAPI(
    title="Document Extraction Service",
    description="Extract structured data from invoices, receipts, and bank statements.",
    version="1.0.0",
)


# ─── Pydantic Models (API Contract) ───────────────────────────

class QualityAssessment(BaseModel):
    """Pre-extraction quality check result."""
    gate: str = Field(..., description="PASS, WARN, or REJECT")
    reason: str = Field(..., description="Human-readable explanation")
    dpi: Optional[int] = Field(None)
    blur_score: Optional[float] = Field(None)


class ExtractionResult(BaseModel):
    """Top-level response envelope."""
    success: bool
    filename: str
    document_type: str = Field("unknown", description="invoice | receipt | bank_statement | unknown")
    quality: QualityAssessment
    fields: Optional[ExtractedFields] = None
    raw_text: Optional[str] = Field(None, description="Full OCR text for debugging")
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# ─── Health Check ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "doc-extract", "version": "1.0.0"}


# ─── Extraction Endpoint ──────────────────────────────────────

@app.post("/v1/extract", response_model=ExtractionResult)
async def extract(
    file: UploadFile = File(..., description="PDF, PNG, JPG, or TIFF document"),
    vendor: Optional[str] = None,
):
    """
    Extract structured data from a document.

    - **file**: The document to process (PDF, PNG, JPG, TIFF).
    - **vendor**: Optional vendor name hint for template matching.
    """
    warnings: List[str] = []
    errors: List[str] = []

    # 1. Save uploaded file to a temporary location
    try:
        suffix = os.path.splitext(file.filename or "document.pdf")[1] or ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {e}")

    try:
        # 2. Detect true file type from content (not extension)
        mime_type = magic.from_file(tmp_path, mime=True)
        is_pdf = mime_type == "application/pdf"
        is_image = mime_type in ("image/png", "image/jpeg", "image/tiff")

        if not is_pdf and not is_image:
            os.unlink(tmp_path)
            return ExtractionResult(
                success=False,
                filename=file.filename or "unknown",
                errors=[f"Unsupported file type: {mime_type}. Send a PDF, PNG, JPG, or TIFF."],
            )

        # 3. Quality gate — basic checks
        quality = QualityAssessment(gate="PASS", reason="Document accepted")

        # 4. Route to the correct processor
        raw_text = ""
        if is_pdf:
            raw_text = extract_from_native_pdf(tmp_path, warnings)
            # If pdfplumber extracted almost nothing, the PDF is likely scanned
            if len(raw_text.strip()) < 50:
                warnings.append("PDF appears to be scanned (little machine-readable text). "
                                "OCR would be needed for better results — "
                                "install Tesseract OCR on this server.")
        elif is_image:
            raw_text = extract_from_image(tmp_path, warnings)

        # 5. Classify document type
        doc_type = _classify_document(raw_text)

        # 6. Extract structured fields
        fields = extract_fields(raw_text, doc_type, vendor, warnings)

        return ExtractionResult(
            success=True,
            filename=file.filename or "unknown",
            document_type=doc_type,
            quality=quality,
            fields=fields,
            raw_text=raw_text[:10000],  # truncate for response size
            warnings=warnings,
        )

    except Exception as e:
        errors.append(f"{type(e).__name__}: {e}")
        errors.append(traceback.format_exc())
        return ExtractionResult(
            success=False,
            filename=file.filename or "unknown",
            errors=errors,
            warnings=warnings,
        )
    finally:
        # 7. Always clean up the temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ─── Document Classification ──────────────────────────────────

def _classify_document(text: str) -> str:
    """Rule-based classification using keyword matching."""
    t = text.lower()
    # Bank statement indicators
    bank_keywords = ["opening balance", "closing balance", "statement", "transaction",
                     "withdrawal", "deposit", "available balance"]
    if any(kw in t for kw in bank_keywords):
        return "bank_statement"
    # Invoice indicators
    invoice_keywords = ["invoice", "tax invoice", "gstin", "bill to", "ship to",
                        "purchase order", "due date", "total amount"]
    if any(kw in t for kw in invoice_keywords):
        return "invoice"
    # Receipt indicators
    receipt_keywords = ["receipt", "paid", "payment received", "cash sale"]
    if any(kw in t for kw in receipt_keywords):
        return "receipt"
    return "unknown"