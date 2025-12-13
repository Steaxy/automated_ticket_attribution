from __future__ import annotations
from collections.abc import Sequence
from app.application.ports.helpdesk_service_port import HelpdeskRequestProvider
from app.domain.helpdesk import HelpdeskRequest
from app.infrastructure.helpdesk_client import HelpdeskClient


class HelpdeskClientRequestProvider(HelpdeskRequestProvider):
    def __init__(self, client: HelpdeskClient) -> None:
        self._client = client

    def fetch_requests(self) -> Sequence[HelpdeskRequest]:
        fetched = self._client.fetch_requests()
        return [f.request for f in fetched]