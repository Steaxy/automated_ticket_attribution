from __future__ import annotations
from dataclasses import dataclass


@dataclass(slots=True)
class HelpdeskRequest:
    id: str | None
    short_description: str | None
    long_description: str | None = None
    request_category: str | None = None
    request_type: str | None = None
    sla_unit: str | None = None
    sla_value: int | None = None