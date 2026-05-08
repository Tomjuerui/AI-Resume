class PdfParseError(Exception):
    """Raised when PDF parsing fails."""
    pass


class ScannedPdfError(PdfParseError):
    """Raised when PDF is scanned/image-based with no extractable text."""
    pass


class LLMCallError(Exception):
    """Raised when LLM API call fails."""
    pass


class OSSUploadError(Exception):
    """Raised when OSS upload fails."""
    pass


class FileValidationError(Exception):
    """Raised when uploaded file fails validation."""
    pass


class CacheError(Exception):
    """Raised when cache operations fail."""
    pass
