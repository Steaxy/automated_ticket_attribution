from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class HelpdeskRequest:
    raw_id: Optional[str]
    short_description: Optional[str]
    raw_payload: Dict[str, Any]
    request_category: Optional[str] = None
    request_type: Optional[str] = None
    sla_unit: Optional[str] = None
    sla_value: Optional[int] = None