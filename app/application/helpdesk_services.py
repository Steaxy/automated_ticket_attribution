from typing import List
from app.domain.helpdesk import HelpdeskRequest
from app.application.ports.helpdesk_service_port import HelpdeskRequestProvider


class HelpdeskService:
    def __init__(self, provider: HelpdeskRequestProvider) -> None:
        self._provider = provider

    def load_helpdesk_requests(self) -> List[HelpdeskRequest]:
        return self._provider.fetch_requests()