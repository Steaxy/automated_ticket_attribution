from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class HelpdeskRequest:
    raw_id: Optional[str]
    short_description: Optional[str]
    raw_payload: Dict[str, Any]