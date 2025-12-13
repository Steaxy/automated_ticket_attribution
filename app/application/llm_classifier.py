from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Callable
from app.domain.helpdesk import HelpdeskRequest
from app.domain.service_catalog import ServiceCatalog


@dataclass(frozen=True)
class LLMClassificationResult:
    request_category: Optional[str]
    request_type: Optional[str]

class LLMClassificationError(RuntimeError):
    """Raised when LLM classification fails in a non-recoverable way."""

LLMClassifierFn = Callable[
    [HelpdeskRequest, ServiceCatalog],
    LLMClassificationResult,
]