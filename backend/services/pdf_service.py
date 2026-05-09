import hashlib
import re
from pathlib import Path

from core.exceptions import PdfParseError, ScannedPdfError


async def extract_text(file_path: Path) -> str:
    """Extract text from a PDF using pdfplumber, with PyMuPDF fallback."""
    text = await _extract_with_pdfplumber(file_path)

    if not text.strip():
        # Fallback to PyMuPDF
        text = await _extract_with_pymupdf(file_path)

    return text


async def _extract_with_pdfplumber(file_path: Path) -> str:
    import pdfplumber

    text_parts: list[str] = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as e:
        raise PdfParseError(f"PDF parsing failed: {e}") from e

    return "\n".join(text_parts)


async def _extract_with_pymupdf(file_path: Path) -> str:
    import fitz  # PyMuPDF

    text_parts: list[str] = []
    try:
        doc = fitz.open(file_path)
        for page in doc:
            page_text = page.get_text()
            if page_text:
                text_parts.append(page_text)
        doc.close()
    except Exception as e:
        raise PdfParseError(f"PyMuPDF fallback parsing failed: {e}") from e

    return "\n".join(text_parts)


def clean_text(text: str) -> str:
    """Clean and normalize extracted PDF text.

    Steps:
    1. Remove control characters (keep CJK, ASCII letters/digits, common punctuation)
    2. Normalize whitespace: collapse 3+ newlines into 2
    3. Strip trailing whitespace per line
    """
    # Replace control chars (except \n, \t, \r) with spaces
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', ' ', text)

    # Keep printable CJK + ASCII + common punctuation
    # \u4e00-\u9fff = CJK Unified Ideographs
    # \u3000-\u303f = CJK Symbols and Punctuation
    # \uff00-\uffef = Halfwidth and Fullwidth Forms
    text = re.sub(r'[^\u4e00-\u9fff\u3000-\u303f\uff00-\uffef'
                  r'\x20-\x7e\u00a0-\u00ff\u2000-\u206f\n\r\t]', ' ', text)

    # Replace carriage returns
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Collapse 3+ newlines into 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Strip whitespace per line
    lines = [line.strip() for line in text.split('\n')]

    # Remove leading/trailing empty lines
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()

    return '\n'.join(lines)


def is_scanned_pdf(text: str) -> bool:
    """Check whether the extracted text indicates a scanned/image-based PDF.

    Returns True if text is effectively empty (scanned PDF with no OCR layer).
    """
    # Remove whitespace and check if anything remains
    stripped = re.sub(r'\s+', '', text)
    return len(stripped) == 0


def compute_md5(file_path: Path) -> str:
    """Compute MD5 hash of a file (for cache key)."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_md5_bytes(data: bytes) -> str:
    """Compute MD5 hash of bytes (for cache key without file I/O)."""
    return hashlib.md5(data).hexdigest()
