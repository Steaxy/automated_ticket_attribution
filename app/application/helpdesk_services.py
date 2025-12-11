from app.domain.helpdesk import HelpdeskRequest
from app.application.ports.helpdesk_service_port import HelpdeskRequestProvider
import logging
from collections.abc import Sequence


logger = logging.getLogger(__name__)

class HelpdeskService:
    def __init__(self, provider: HelpdeskRequestProvider) -> None:
        self._provider = provider

    def load_helpdesk_requests(self) -> Sequence[HelpdeskRequest]:
        logger.debug(
            "Loading helpdesk requests from provider %s",
            type(self._provider).__name__,
        )
        requests_ = self._provider.fetch_requests()
        logger.debug(
            "Loaded %d helpdesk request(s) from provider %s",
            len(requests_),
            type(self._provider).__name__,
        )
        return requests_