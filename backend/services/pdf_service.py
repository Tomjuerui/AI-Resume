import hashlib
from pathlib import Path


async def extract_text(file_path: Path) -> str:
    """Extract and clean text from a PDF file."""
    import pdfplumber

    text_parts: list[str] = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def compute_md5(file_path: Path) -> str:
    """Compute MD5 hash of a file (for cache key)."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
