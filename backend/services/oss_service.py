import uuid
from datetime import datetime

import oss2
from core.config import settings
from core.exceptions import OSSUploadError


def _get_bucket():
    """Create and return an OSS Bucket instance."""
    auth = oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
    return oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket)


async def upload_pdf(file_bytes: bytes, filename: str) -> str:
    """Upload a PDF to OSS and return its public URL.

    The object key follows the pattern: resumes/YYYY-MM-DD/{uuid}.pdf
    """
    if not settings.oss_configured:
        raise OSSUploadError("OSS not configured")

    date_prefix = datetime.now().strftime("%Y-%m-%d")
    key = f"resumes/{date_prefix}/{uuid.uuid4()}.pdf"

    try:
        bucket = _get_bucket()
        bucket.put_object(key, file_bytes, headers={"Content-Type": "application/pdf"})
    except oss2.exceptions.OssError as e:
        raise OSSUploadError(f"OSS upload failed: {e}") from e

    # Build public URL
    url = f"https://{settings.oss_bucket}.{settings.oss_endpoint}/{key}"
    return url
