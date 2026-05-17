"""
Structured field extraction from raw OCR text.
Uses invoice2data templates for known vendors,
regex rules as fallback for unknown formats.
"""

import re
from typing import List, Optional
from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: str = ""
    quantity: float = 0.0
    rate: float = 0.0
    amount: float = 0.0


class ExtractedFields(BaseModel):
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    total_amount: Optional[float] = None
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    gstin: Optional[str] = None
    line_items: List[LineItem] = Field(default_factory=list)
    currency: str = "INR"


def extract_fields(
    text: str,
    doc_type: str = "unknown",
    vendor: Optional[str] = None,
    warnings: Optional[List[str]] = None,
) -> ExtractedFields:
    """
    Extract structured fields from raw text.
    Tries invoice2data templates first, then regex fallback.
    """
    if warnings is None:
        warnings = []

    # --- Attempt invoice2data if it's an invoice ---
    if doc_type == "invoice":
        try:
            from invoice2data.extract import extract_data
            from invoice2data.extract.loader import read_templates
            # Look for templates in the templates/ directory
            import os
            template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
            if os.path.isdir(template_dir):
                templates = read_templates(template_dir)
                # invoice2data expects a file path, not raw text
                # We'll use regex fallback for now (see below)
        except ImportError:
            warnings.append("invoice2data not installed — using regex fallback.")

    # --- Regex Fallback Extraction ---
    fields = ExtractedFields()

    # Vendor name: first non-empty line that looks like a company name
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in lines[:10]:
        if len(line) > 3 and not re.match(r"^[\d\s,.₹$%/-]+$", line):
            fields.vendor_name = line
            break

    # GSTIN: 2-digit state code + 10 PAN chars + 1 entity + Z + 1 check
    gstin_match = re.search(r"\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1}", text)
    if gstin_match:
        fields.gstin = gstin_match.group(0)

    # Invoice number: common patterns
    inv_patterns = [
        r"(?:Invoice|Bill|INV)\s*(?:No|#|Number)?[:.]?\s*([A-Za-z0-9/\-]+)",
        r"(?:Invoice|Bill)\s*#\s*([A-Za-z0-9/\-]+)",
    ]
    for pat in inv_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            fields.invoice_number = m.group(1).strip()
            break

    # Date: look for ISO-like or common Indian date patterns
    date_patterns = [
        r"Date\s*[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(\d{2}/\d{2}/\d{4})",
        r"(\d{4}-\d{2}-\d{2})",
    ]
    for pat in date_patterns:
        m = re.search(pat, text)
        if m:
            fields.invoice_date = m.group(1)
            break

    # Total amount: largest currency-like number near keywords
    total_patterns = [
        r"(?:Total|Grand Total|Amount Payable|Net Amount)\s*[:.]?\s*[₹$]?\s*([\d,]+\.?\d{0,2})",
        r"(?:TOTAL|AMOUNT)\s*[:.]?\s*[₹$]?\s*([\d,]+\.?\d{0,2})",
    ]
    for pat in total_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                fields.total_amount = float(m.group(1).replace(",", ""))
            except ValueError:
                pass
            break

    # If no explicit total found, take the largest number on the page
    if fields.total_amount is None:
        all_numbers = re.findall(r"(?:₹|INR|Rs\.?)\s*([\d,]+\.?\d{0,2})", text)
        if not all_numbers:
            all_numbers = re.findall(r"([\d,]+\.\d{2})", text)
        if all_numbers:
            try:
                fields.total_amount = max(float(n.replace(",", "")) for n in all_numbers)
            except ValueEr"""
Structured field extraction from raw OCR text.
Uses invoice2data templates for known vendors,
regex rules as fallback for unknown formats.
"""

import re
from typing import List, Optional
from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: str = ""
    quantity: float = 0.0
    rate: float = 0.0
    amount: float = 0.0


class ExtractedFields(BaseModel):
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    total_amount: Optional[float] = None
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    gstin: Optional[str] = None
    line_items: List[LineItem] = Field(default_factory=list)
    currency: str = "INR"


def extract_fields(
    text: str,
    doc_type: str = "unknown",
    vendor: Optional[str] = None,
    warnings: Optional[List[str]] = None,
) -> ExtractedFields:
    """
    Extract structured fields from raw text.
    Tries invoice2data templates first, then regex fallback.
    """
    if warnings is None:
        warnings = []

    # --- Attempt invoice2data if it's an invoice ---
    if doc_type == "invoice":
        try:
            from invoice2data.extract import extract_data
            from invoice2data.extract.loader import read_templates
            # Look for templates in the templates/ directory
            import os
            template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
            if os.path.isdir(template_dir):
                templates = read_templates(template_dir)
                # invoice2data expects a file path, not raw text
                # We'll use regex fallback for now (see below)
        except ImportError:
            warnings.append("invoice2data not installed — using regex fallback.")

    # --- Regex Fallback Extraction ---
    fields = ExtractedFields()

    # Vendor name: first non-empty line that looks like a company name
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in lines[:10]:
        if len(line) > 3 and not re.match(r"^[\d\s,.₹$%/-]+$", line):
            fields.vendor_name = line
            break

    # GSTIN: 2-digit state code + 10 PAN chars + 1 entity + Z + 1 check
    gstin_match = re.search(r"\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1}", text)
    if gstin_match:
        fields.gstin = gstin_match.group(0)

    # Invoice number: common patterns
    inv_patterns = [
        r"(?:Invoice|Bill|INV)\s*(?:No|#|Number)?[:.]?\s*([A-Za-z0-9/\-]+)",
        r"(?:Invoice|Bill)\s*#\s*([A-Za-z0-9/\-]+)",
    ]
    for pat in inv_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            fields.invoice_number = m.group(1).strip()
            break

    # Date: look for ISO-like or common Indian date patterns
    date_patterns = [
        r"Date\s*[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(\d{2}/\d{2}/\d{4})",
        r"(\d{4}-\d{2}-\d{2})",
    ]
    for pat in date_patterns:
        m = re.search(pat, text)
        if m:
            fields.invoice_date = m.group(1)
            break

    # Total amount: largest currency-like number near keywords
    total_patterns = [
        r"(?:Total|Grand Total|Amount Payable|Net Amount)\s*[:.]?\s*[₹$]?\s*([\d,]+\.?\d{0,2})",
        r"(?:TOTAL|AMOUNT)\s*[:.]?\s*[₹$]?\s*([\d,]+\.?\d{0,2})",
    ]
    for pat in total_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                fields.total_amount = float(m.group(1).replace(",", ""))
            except ValueError:
                pass
            break

    # If no explicit total found, take the largest number on the page
    if fields.total_amount is None:
        all_numbers = re.findall(r"(?:₹|INR|Rs\.?)\s*([\d,]+\.?\d{0,2})", text)
        if not all_numbers:
            all_numbers = re.findall(r"([\d,]+\.\d{2})", text)
        if all_numbers:
            try:
                fields.total_amount = max(float(n.replace(",", "")) for n in all_numbers)
            except ValueError:
                pass

    return fieldsror:
                pass

    return fields