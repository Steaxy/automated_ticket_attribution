from typing import List
from app.domain.helpdesk import HelpdeskRequest
from app.infrastructure.helpdesk_client import HelpdeskClient


class HelpdeskService:
    def __init__(self, client: HelpdeskClient) -> None:
        self._client = client

    def load_helpdesk_requests(self) -> List[HelpdeskRequest]:
        return self._client.fetch_requests()