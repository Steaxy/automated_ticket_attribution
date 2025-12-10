from __future__ import annotations
from typing import List, Protocol
from app.domain.helpdesk import HelpdeskRequest


class HelpdeskRequestProvider(Protocol):
    def fetch_requests(self) -> List[HelpdeskRequest]:
        ...