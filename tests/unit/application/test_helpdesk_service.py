from app.application.helpdesk_services import HelpdeskService
from app.domain.helpdesk import HelpdeskRequest
from app.application.ports.helpdesk_service_port import HelpdeskRequestProvider


class FakeHelpdeskRequestProvider(HelpdeskRequestProvider):
    def __init__(self, result: list[HelpdeskRequest]) -> None:
        self._result = result
        self.called = 0

    def fetch_requests(self) -> list[HelpdeskRequest]:
        self.called += 1
        return self._result

def test_helpdesk_service_delegates_to_client() -> None:
    expected = [HelpdeskRequest(id="x", short_description="y")]
    provider = FakeHelpdeskRequestProvider(expected)

    service = HelpdeskService(provider)

    result = service.load_helpdesk_requests()

    assert result == expected
    assert provider.called == 1