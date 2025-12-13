from __future__ import annotations
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Mapping
from app.application.classify_helpdesk_requests import classify_requests
from app.application.llm_classifier import LLMClassificationError, LLMClassificationResult
from app.application.fill_helpdesk_sla import fill_helpdesk_sla
from app.domain.helpdesk import HelpdeskRequest
from app.domain.service_catalog import ServiceCatalog, ServiceCategory, ServiceRequestType, SLA


@dataclass(frozen=True)
class DummySLA:
    unit: str
    value: int

@dataclass(frozen=True)
class DummyRequestType:
    name: str
    sla: DummySLA

@dataclass(frozen=True)
class DummyCategory:
    name: str
    requests: list[DummyRequestType]

@dataclass(frozen=True)
class DummyCatalog:
    categories: list[DummyCategory]

def _make_request(id: str) -> HelpdeskRequest:
    return HelpdeskRequest(
        id=id,
        short_description=f"test {id}",
    )

class FakeClassifier:
    def __init__(
        self,
        results_by_id: dict[str, LLMClassificationResult],
        fail_on_call: int | None = None,
    ) -> None:
        self._results_by_id = results_by_id
        self._fail_on_call = fail_on_call
        self.calls: int = 0
        self.batches: list[Sequence[HelpdeskRequest]] = []

    def classify_batch(
        self,
        requests: Sequence[HelpdeskRequest],
        service_catalog: ServiceCatalog,
    ) -> Mapping[str, LLMClassificationResult]:
        self.calls += 1
        self.batches.append(requests)

        if self._fail_on_call is not None and self.calls == self._fail_on_call:
            raise LLMClassificationError("boom")

        return {
            r.id: self._results_by_id[r.id]
            for r in requests
            if r.id in self._results_by_id
        }

def test_flow_classify_then_derive_sla_happy_path() -> None:
    req1 = _make_request("r1")
    req2 = _make_request("r2")
    requests = [req1, req2]

    catalog = _make_catalog()

    llm_results = {
        "r1": LLMClassificationResult(
            request_category="Access",
            request_type="Password reset",
        ),
        "r2": LLMClassificationResult(
            request_category="Hardware",
            request_type="Laptop issue",
        ),
    }
    classifier = FakeClassifier(results_by_id=llm_results)

    classified = classify_requests(
        classifier=classifier,
        service_catalog=catalog,
        requests_=requests,
        batch_size=10,
        examples_to_log=0,
    )

    fill_helpdesk_sla(classified, catalog)                                                                                      # type: ignore[arg-type]

    assert [r.id for r in classified] == ["r1", "r2"]

    assert req1.request_category == "Access"
    assert req1.request_type == "Password reset"
    assert req1.sla_unit == "hours"
    assert req1.sla_value == 4

    assert req2.request_category == "Hardware"
    assert req2.request_type == "Laptop issue"
    assert req2.sla_unit == "days"
    assert req2.sla_value == 1

    assert classifier.calls == 1

def test_flow_batch_failure_does_not_derive_sla_for_failed_batch() -> None:
    req1 = _make_request("r1")
    req2 = _make_request("r2")
    req3 = _make_request("r3")
    requests = [req1, req2, req3]

    catalog = _make_catalog()

    llm_results = {
        "r1": LLMClassificationResult(
            request_category="Cat1",
            request_type="Type1",
        ),
        # r2 intentionally missing
        "r3": LLMClassificationResult(
            request_category="Cat3",
            request_type="Type3",
        ),
    }

    classifier = FakeClassifier(results_by_id=llm_results, fail_on_call=2)

    classified = classify_requests(
        classifier=classifier,
        service_catalog=catalog,
        requests_=requests,
        batch_size=2,
        examples_to_log=0,
    )

    fill_helpdesk_sla(classified, catalog)

    assert [r.id for r in classified] == ["r1", "r2", "r3"]

    # first batch OK: r1 classified -> SLA derived
    assert req1.request_category == "Cat1"
    assert req1.request_type == "Type1"
    assert req1.sla_unit == "hours"
    assert req1.sla_value == 2

    # r2 had no LLM result -> stays untouched -> SLA not derived
    assert req2.request_category is None
    assert req2.request_type is None
    assert req2.sla_unit is None
    assert req2.sla_value is None

    # second batch failed -> r3 stays untouched -> SLA not derived
    assert req3.request_category is None
    assert req3.request_type is None
    assert req3.sla_unit is None
    assert req3.sla_value is None

def _make_catalog() -> ServiceCatalog:
    return ServiceCatalog(
        categories=[
            ServiceCategory(
                name="Access",
                requests=[ServiceRequestType(name="Password reset", sla=SLA(unit="hours", value=4))],
            ),
            ServiceCategory(
                name="Hardware",
                requests=[ServiceRequestType(name="Laptop issue", sla=SLA(unit="days", value=1))],
            ),
            ServiceCategory(
                name="Cat1",
                requests=[ServiceRequestType(name="Type1", sla=SLA(unit="hours", value=2))],
            ),
            ServiceCategory(
                name="Cat3",
                requests=[ServiceRequestType(name="Type3", sla=SLA(unit="days", value=1))],
            ),
        ]
    )