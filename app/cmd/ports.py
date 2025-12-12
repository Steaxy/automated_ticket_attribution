from typing import Any, Protocol
from pathlib import Path
from collections.abc import Sequence
from app.domain.helpdesk import HelpdeskRequest


class ServiceCatalogClientPort(Protocol):
    def fetch_catalog(self) -> Any:
        ...

class ReportLogPort(Protocol):
    def get_record(self, path: Path) -> Any:
        ...

    def mark_sent(self, path: Path, created_at: Any) -> None:
        ...

class HelpdeskServicePort(Protocol):
    def load_helpdesk_requests(self) -> Sequence[HelpdeskRequest]:
        ...