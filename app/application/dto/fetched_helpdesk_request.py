from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping
from app.domain.helpdesk import HelpdeskRequest


@dataclass(frozen=True, slots=True)
class FetchedHelpdeskRequest:
    request: HelpdeskRequest
    raw_payload: Mapping[str, Any]