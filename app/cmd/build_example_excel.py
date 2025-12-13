from __future__ import annotations
import logging
from app.domain.helpdesk import HelpdeskRequest
from app.infrastructure.save_excel import save_excel


logger = logging.getLogger(__name__)

def _make_mock_requests() -> list[HelpdeskRequest]:
    return [
        HelpdeskRequest(
            id="req_1",
            request_category="Access Management",
            request_type="Reset forgotten password",
            short_description="User cannot log in to Okta",
            sla_value=4,
            sla_unit="hours",                                                                                                 # type: ignore[arg-type]
        ),
        HelpdeskRequest(
            id="req_2",
            request_category="Hardware Support",
            request_type="Laptop Repair/Replacement",
            short_description="Laptop not turning on",
            sla_value=7,
            sla_unit="days",
        ),
    ]

def main() -> None:
    requests = _make_mock_requests()
    save_excel(requests, filename_prefix="example_")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()