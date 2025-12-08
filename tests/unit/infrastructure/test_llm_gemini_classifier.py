import json
from typing import Any
from unittest.mock import Mock, patch
import pytest
from app.config import LLMConfig
from app.domain.helpdesk import HelpdeskRequest
from app.domain.service_catalog import ServiceCatalog, ServiceCategory, ServiceRequestType, SLA
from app.application.llm_classifier import LLMClassificationResult, LLMClassificationError
from app.infrastructure.llm_gemini_classifier import GeminiLLMClassifier


@patch("app.infrastructure.llm_gemini_classifier.genai.Client")
def test_classify_helpdesk_request_happy_path(mock_client_cls: Mock) -> None:
    config = LLMConfig(
        model_name="test-model",
        api_key="test-api-key",
    )

    mock_client = Mock()
    mock_client_cls.return_value = mock_client

    payload: dict[str, Any] = {
        "request_category": "Access Management",
        "request_type": "Reset password",
        "sla_unit": "hours",
        "sla_value": 4,
    }

    mock_response = Mock()
    mock_response.text = json.dumps(payload)
    mock_client.models.generate_content.return_value = mock_response

    classifier = GeminiLLMClassifier(config)

    request = HelpdeskRequest(
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
                requests=[
                    ServiceRequestType(
                        name="Reset password",
                        sla=SLA(unit="hours", value=4),
                    )
                ],
            )
        ]
    )

    # act
    result = classifier.classify_helpdesk_request(request, catalog)

    # assert
    assert isinstance(result, LLMClassificationResult)
    assert result.request_category == "Access Management"
    assert result.request_type == "Reset password"
    assert result.sla_unit == "hours"
    assert result.sla_value == 4

@patch("app.infrastructure.llm_gemini_classifier.genai.Client")
def test_classify_helpdesk_request_raises_on_non_json(mock_client_cls: Mock) -> None:
    config = LLMConfig(
        model_name="test-model",
        api_key="test-api-key",
    )

    mock_client = Mock()
    mock_client_cls.return_value = mock_client

    mock_response = Mock()
    mock_response.text = "this is not json"
    mock_client.models.generate_content.return_value = mock_response

    classifier = GeminiLLMClassifier(config)

    request = HelpdeskRequest(
        raw_id="req_1",
        short_description="Anything",
        raw_payload={},
        request_category=None,
        request_type=None,
        sla_unit=None,
        sla_value=None,
    )

    catalog = ServiceCatalog(categories=[])

    with pytest.raises(LLMClassificationError, match="Gemini output was not valid JSON"):
        _ = classifier.classify_helpdesk_request(request, catalog)


@patch("app.infrastructure.llm_gemini_classifier.genai.Client")
def test_classify_helpdesk_request_raises_when_text_empty(mock_client_cls: Mock) -> None:
    config = LLMConfig(
        model_name="test-model",
        api_key="test-api-key",
    )

    mock_client = Mock()
    mock_client_cls.return_value = mock_client

    mock_response = Mock()
    mock_response.text = "   "                                              # only whitespace -> treated as empty
    mock_client.models.generate_content.return_value = mock_response

    classifier = GeminiLLMClassifier(config)

    request = HelpdeskRequest(
        raw_id="req_1",
        short_description="Anything",
        raw_payload={},
        request_category=None,
        request_type=None,
        sla_unit=None,
        sla_value=None,
    )

    catalog = ServiceCatalog(categories=[])

    with pytest.raises(LLMClassificationError, match="contained no text"):
        _ = classifier.classify_helpdesk_request(request, catalog)