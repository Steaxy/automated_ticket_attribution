from typing import Any
from unittest.mock import Mock
import pytest
from app.config import HelpdeskAPIConfig
from app.infrastructure.helpdesk_client import HelpdeskClient, HelpdeskAPIError
from app.application.dto.fetched_helpdesk_request import FetchedHelpdeskRequest
from requests import HTTPError


def _make_client_with_mock_session(json_payload: Any) -> HelpdeskClient:
    config = HelpdeskAPIConfig(
        url="https://example.com/helpdesk",
        api_key="dummy-key",
        api_secret="dummy-secret",
        timeout_seconds=5.0,
    )

    client = HelpdeskClient(config)

    mock_session = Mock()
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json = Mock(return_value=json_payload)

    mock_session.post = Mock(return_value=mock_response)

    client._session = mock_session                                                                                          # type: ignore[attr-defined]
    return client

def test_fetch_requests_happy_path() -> None:
    sample_data: dict[str, Any] = {
        "response_code": 200,
        "data": {
            "requests": [
                {
                    "id": "req_101",
                    "short_description": "Forgot my Okta password",
                    "long_description": "dummy",
                    "requester_email": "j.doe@company.com",
                    "request_category": "",
                    "request_type": "",
                    "sla": {"unit": "", "value": 0},
                }
            ]
        },
    }

    client = _make_client_with_mock_session(sample_data)

    result: list[FetchedHelpdeskRequest] = client.fetch_requests()

    assert len(result) == 1
    fetched = result[0]
    assert fetched.request.id == "req_101"
    assert fetched.request.short_description == "Forgot my Okta password"
    assert fetched.raw_payload["requester_email"] == "j.doe@company.com"

def test_fetch_requests_unexpected_shape_raises() -> None:
    bad_data = {
        "response_code": 200,
        "data": {"not_requests": []},
    }

    client = _make_client_with_mock_session(bad_data)

    with pytest.raises(HelpdeskAPIError):
        _ = client.fetch_requests()

def test_fetch_raw_returns_json() -> None:
    sample_data = {"foo": "bar"}
    client = _make_client_with_mock_session(sample_data)

    raw = client.fetch_raw()
    assert raw == sample_data

def test_http_error_is_wrapped_in_helpdesk_api_error() -> None:
    config = HelpdeskAPIConfig(
        url="https://example.com/helpdesk",
        api_key="dummy-key",
        api_secret="dummy-secret",
        timeout_seconds=5.0,
    )

    client = HelpdeskClient(config)

    mock_session = Mock()
    mock_response = Mock()

    mock_response.raise_for_status.side_effect = HTTPError("404 not found")
    mock_session.post.return_value = mock_response

    client._session = mock_session                                                                                          # type: ignore[attr-defined]

    with pytest.raises(HelpdeskAPIError):
        _ = client.fetch_requests()

def test_json_error_is_wrapped_in_helpdesk_api_error() -> None:
    config = HelpdeskAPIConfig(
        url="https://example.com/helpdesk",
        api_key="dummy-key",
        api_secret="dummy-secret",
        timeout_seconds=5.0,
    )

    client = HelpdeskClient(config)

    mock_session = Mock()
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.side_effect = ValueError("invalid json")

    mock_session.post.return_value = mock_response
    client._session = mock_session                                                                                          # type: ignore[attr-defined]

    with pytest.raises(HelpdeskAPIError):
        _ = client.fetch_requests()

def test_fetch_requests_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    # avoid real sleep during tests
    monkeypatch.setattr("app.infrastructure.helpdesk_client.time.sleep", lambda _: None)

    config = HelpdeskAPIConfig(
        url="https://example.com/helpdesk",
        api_key="dummy-key",
        api_secret="dummy-secret",
        timeout_seconds=5.0,
    )
    client = HelpdeskClient(config, max_retries=3, backoff_factor=0.0)

    mock_session = Mock()

    # first call -> HTTPError, second call -> ok
    bad_response = Mock()
    bad_response.raise_for_status.side_effect = HTTPError("503")

    ok_payload: dict[str, Any] = {
        "data": {"requests": [{"id": "req_1", "short_description": "hi"}]},
    }
    ok_response = Mock()
    ok_response.raise_for_status = Mock()
    ok_response.json = Mock(return_value=ok_payload)

    mock_session.post.side_effect = [bad_response, ok_response]
    client._session = mock_session  # type: ignore[attr-defined]

    result = client.fetch_requests()
    assert len(result) == 1
    assert result[0].request.id == "req_1"
    assert mock_session.post.call_count == 2

def test_fetch_requests_retries_exhausted_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # avoid real sleep during tests
    monkeypatch.setattr("app.infrastructure.helpdesk_client.time.sleep", lambda _: None)

    config = HelpdeskAPIConfig(
        url="https://example.com/helpdesk",
        api_key="dummy-key",
        api_secret="dummy-secret",
        timeout_seconds=5.0,
    )
    client = HelpdeskClient(config, max_retries=3, backoff_factor=0.0)

    mock_session = Mock()
    failing_response = Mock()
    failing_response.raise_for_status.side_effect = HTTPError("500")
    mock_session.post.return_value = failing_response
    client._session = mock_session                                                                                          # type: ignore[attr-defined]

    with pytest.raises(HelpdeskAPIError):
        client.fetch_requests()

    assert mock_session.post.call_count == 3

def test_fetch_requests_supports_top_level_list() -> None:
    payload = [{"id": "req_1", "short_description": "a"}]
    client = _make_client_with_mock_session(payload)

    result = client.fetch_requests()
    assert result[0].request.id == "req_1"


def test_fetch_requests_supports_data_as_list() -> None:
    payload = {"data": [{"id": "req_1", "short_description": "a"}]}
    client = _make_client_with_mock_session(payload)

    result = client.fetch_requests()
    assert result[0].request.id == "req_1"