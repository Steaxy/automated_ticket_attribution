from __future__ import annotations
from dataclasses import dataclass
from app.application.fill_helpdesk_sla import fill_helpdesk_sla


@dataclass
class DummySLA:
    unit: str
    value: int

@dataclass
class DummyRequestType:
    name: str
    sla: DummySLA

@dataclass
class DummyCategory:
    name: str
    requests: list[DummyRequestType]

@dataclass
class DummyCatalog:
    categories: list[DummyCategory]

@dataclass
class DummyHelpdeskRequest:
    id: str
    request_category: str | None = None
    request_type: str | None = None
    sla_unit: str | None = None
    sla_value: int | None = None

# fills SLA when category+type match and SLA is None
def test_fill_helpdesk_sla_fills_when_missing_and_match() -> None:
    catalog = DummyCatalog(
        categories=[
            DummyCategory(
                name="Other/Uncategorized",
                requests=[
                    DummyRequestType("General Inquiry/Undefined", DummySLA("hours", 0)),
                ],
            )
        ]
    )

    req = DummyHelpdeskRequest(
        id="req_1",
        request_category="Other/Uncategorized",
        request_type="General Inquiry/Undefined",
        sla_unit=None,
        sla_value=None,
    )

    fill_helpdesk_sla([req], catalog)                                                                                                # type: ignore[arg-type]

    assert req.sla_unit == "hours"
    assert req.sla_value == 0


# does not overwrite SLA when already present
def test_fill_helpdesk_sla_does_not_overwrite_existing_sla() -> None:
    catalog = DummyCatalog(
        categories=[
            DummyCategory(
                name="Access Management",
                requests=[
                    DummyRequestType("Reset forgotten password", DummySLA("hours", 4)),
                ],
            )
        ]
    )

    req = DummyHelpdeskRequest(
        id="req_2",
        request_category="Access Management",
        request_type="Reset forgotten password",
        sla_unit="hours",
        sla_value=8,                                                                                                        # deliberately different from catalog
    )

    fill_helpdesk_sla([req], catalog)                                                                                     # type: ignore[arg-type]

    # value must stay as set by LLM
    assert req.sla_unit == "hours"
    assert req.sla_value == 8


# does nothing when category/type pair is not in catalog
def test_fill_helpdesk_sla_ignores_unknown_category_type() -> None:
    catalog = DummyCatalog(categories=[])

    req = DummyHelpdeskRequest(
        id="req_3",
        request_category="Nonexistent Category",
        request_type="Nonexistent Type",
        sla_unit=None,
        sla_value=None,
    )

    fill_helpdesk_sla([req], catalog)                                                                                                # type: ignore[arg-type]

    assert req.sla_unit is None
    assert req.sla_value is None


# does nothing when category or type is missing on request
def test_fill_helpdesk_sla_skips_when_category_or_type_missing() -> None:
    catalog = DummyCatalog(
        categories=[
            DummyCategory(
                name="Access Management",
                requests=[
                    DummyRequestType("Reset forgotten password", DummySLA("hours", 4)),
                ],
            )
        ]
    )

    req_missing_category = DummyHelpdeskRequest(
        id="req_4",
        request_category=None,
        request_type="Reset forgotten password",
        sla_unit=None,
        sla_value=None,
    )

    req_missing_type = DummyHelpdeskRequest(
        id="req_5",
        request_category="Access Management",
        request_type=None,
        sla_unit=None,
        sla_value=None,
    )

    fill_helpdesk_sla([req_missing_category, req_missing_type], catalog)                                                  # type: ignore[arg-type]

    assert req_missing_category.sla_unit is None
    assert req_missing_category.sla_value is None
    assert req_missing_type.sla_unit is None
    assert req_missing_type.sla_value is None

def test_fill_helpdesk_sla_fills_when_empty_string_or_zero() -> None:
    catalog = DummyCatalog(
        categories=[
            DummyCategory(
                name="Access Management",
                requests=[
                    DummyRequestType("Reset forgotten password", DummySLA("hours", 4)),
                ],
            )
        ]
    )

    req = DummyHelpdeskRequest(
        id="req_empty",
        request_category="Access Management",
        request_type="Reset forgotten password",
        sla_unit="   ",                                                                                                     # empty after strip
        sla_value=0,                                                                                                        # treated as missing
    )

    fill_helpdesk_sla([req], catalog)                                                                                     # type: ignore[arg-type]

    assert req.sla_unit == "hours"
    assert req.sla_value == 4

def test_fill_helpdesk_sla_fills_only_missing_unit() -> None:
    catalog = DummyCatalog(
        categories=[
            DummyCategory(
                name="Hardware",
                requests=[
                    DummyRequestType("Replace keyboard", DummySLA("hours", 8)),
                ],
            )
        ]
    )

    req = DummyHelpdeskRequest(
        id="req_unit",
        request_category="Hardware",
        request_type="Replace keyboard",
        sla_unit=None,
        sla_value=99,
    )

    fill_helpdesk_sla([req], catalog)                                                                                     # type: ignore[arg-type]

    assert req.sla_unit == "hours"
    assert req.sla_value == 99

def test_fill_helpdesk_sla_fills_only_missing_value() -> None:
    catalog = DummyCatalog(
        categories=[
            DummyCategory(
                name="Hardware",
                requests=[
                    DummyRequestType("Replace mouse", DummySLA("hours", 6)),
                ],
            )
        ]
    )

    req = DummyHelpdeskRequest(
        id="req_value",
        request_category="Hardware",
        request_type="Replace mouse",
        sla_unit="hours",
        sla_value=0,                                                                                                        # treated as missing
    )

    fill_helpdesk_sla([req], catalog)                                                                                                # type: ignore[arg-type]

    assert req.sla_unit == "hours"
    assert req.sla_value == 6