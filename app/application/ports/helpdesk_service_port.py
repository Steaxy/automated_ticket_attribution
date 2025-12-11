from __future__ import annotations
from typing import Protocol
from app.domain.helpdesk import HelpdeskRequest
from collections.abc import Sequence


class HelpdeskRequestProvider(Protocol):
    def fetch_requests(self) -> Sequence[HelpdeskRequest]:
        ...