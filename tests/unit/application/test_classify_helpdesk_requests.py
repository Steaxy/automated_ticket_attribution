from typing import List
from app.application.classify_helpdesk_requests import ClassifyHelpdeskRequests
from app.application.llm_classifier import LLMClassificationResult
from app.domain.helpdesk import HelpdeskRequest
from app.domain.service_catalog import ServiceCatalog, ServiceCategory, ServiceRequestType, SLA


def _fake_classifier(_: HelpdeskRequest, __: ServiceCatalog) -> LLMClassificationResult:
    return LLMClassificationResult(
        request_category="Access Management",
        request_type="Reset password",
        sla_unit="hours",
        sla_value=4,
    )

def test_classify_fills_empty_fields() -> None:
    req = HelpdeskRequest(
        raw_id="req_1",
        short_description="Forgot my password",
        raw_payload={},
        request_category=None,
        request_type=None,
        sla_unit=None,
        sla_value=None,
    )

    catalog = ServiceCatalog(
        categories=[
            ServiceCategory(
                name="Access Management",
                requests=[ServiceRequestType(name="Reset password", sla=SLA(unit="hours", value=4))],
            )
        ]
    )

    use_case = ClassifyHelpdeskRequests(classifier=_fake_classifier)

    result: List[HelpdeskRequest] = use_case.execute([req], catalog)

    assert len(result) == 1
    classified = result[0]
    assert classified.request_category == "Access Management"
    assert classified.request_type == "Reset password"
    assert classified.sla_unit == "hours"
    assert classified.sla_value == 4