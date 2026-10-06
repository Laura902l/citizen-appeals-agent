"""Rule-based masking of personal data before an appeal reaches the classifier.

This is a deliberately simple, transparent baseline: phone numbers, e-mail
addresses and self-introduced names ("my name is ...") are replaced by
placeholders. A named-entity-recognition model is planned for the pilot phase.
"""

from __future__ import annotations

import re

PHONE_TOKEN = "[PHONE]"
EMAIL_TOKEN = "[EMAIL]"
NAME_TOKEN = "[NAME]"

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# +7 701 234 56 78, 8(701)234-56-78, +77012345678 ... at least 10 digits.
_PHONE_RE = re.compile(r"(?<!\w)\+?\d(?:[\s\-()]*\d){9,13}(?!\w)")
_NAME_RE = re.compile(
    r"(?P<intro>(?i:my name is|i am|this is|signed|regards,|меня зовут))\s+"
    r"(?P<name>[A-ZА-ЯЁ][a-zа-яё]+(?:\s+[A-ZА-ЯЁ][a-zа-яё]+)?)"
)


def mask_personal_data(text: str) -> str:
    """Return ``text`` with phones, e-mails and introduced names masked."""
    masked = _EMAIL_RE.sub(EMAIL_TOKEN, text)
    masked = _PHONE_RE.sub(PHONE_TOKEN, masked)
    return _NAME_RE.sub(lambda m: f"{m.group('intro')} {NAME_TOKEN}", masked)


def contains_personal_data(text: str) -> bool:
    """``True`` if any supported personal-data pattern is present."""
    return mask_personal_data(text) != text
