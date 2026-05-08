class PdfParseError(Exception):
    """Raised when PDF parsing fails."""
    pass


class LLMCallError(Exception):
    """Raised when LLM API call fails."""
    pass


class CacheError(Exception):
    """Raised when Redis cache operation fails."""
    pass
