from __future__ import annotations
from typing import Any, Optional


def normalize_str_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s or None

def normalize_int_or_none(value: Any, *, allow_zero: bool = False) -> Optional[int]:
    if value is None:
        return None
    try:
        v_int = int(value)
    except (TypeError, ValueError):
        return None

    if not allow_zero and v_int <= 0:
        return None

    return v_int