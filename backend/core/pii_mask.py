"""PII masking utilities for log desensitization.

PRD Section 8.5: "日志中坚决脱敏（隐藏真实姓名、手机号）"
"""

import re


def mask_name(name: str) -> str:
    """Mask a name: 张三 → 张**, John → J***"""
    if not name:
        return ""
    if len(name) <= 1:
        return name
    return name[0] + "*" * (len(name) - 1)


def mask_phone(phone: str) -> str:
    """Mask a phone number: 13812345678 → 138****5678"""
    if not phone:
        return ""
    cleaned = re.sub(r'[\s\-()（）+]', '', phone)
    if len(cleaned) < 7:
        return "*" * len(phone)
    return cleaned[:3] + "****" + cleaned[-4:]


def mask_email(email: str) -> str:
    """Mask an email: zhangsan@example.com → z***@example.com"""
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        masked_local = local + "***"
    else:
        masked_local = local[0] + "***"
    return f"{masked_local}@{domain}"


def mask_pii_dict(data: dict, fields: set[str] | None = None) -> dict:
    """Return a copy of the dict with PII fields masked for logging.

    Default fields: name, phone, email
    """
    if fields is None:
        fields = {"name", "phone", "email"}

    masked = {}
    for key, value in data.items():
        if key == "name" and isinstance(value, str) and value:
            masked[key] = mask_name(value)
        elif key == "phone" and isinstance(value, str) and value:
            masked[key] = mask_phone(value)
        elif key == "email" and isinstance(value, str) and value:
            masked[key] = mask_email(value)
        else:
            masked[key] = value
    return masked
