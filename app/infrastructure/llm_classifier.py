from __future__ import annotations
import json
import logging
from typing import Any
from app.application.llm_classifier import (
    LLMClassificationResult,
    LLMClassificationError,
)
from app.domain.helpdesk import HelpdeskRequest
from app.domain.service_catalog import ServiceCatalog
from app.config import LLMConfig
from google import genai
from google.genai import types
from app.shared.normalization import normalize_str_or_none, normalize_int_or_none
from app.infrastructure.llm_classifier_prompt import LLM_BATCH_PROMPT_TEMPLATE
from typing import Sequence


logger = logging.getLogger(__name__)

class LLMClassifier:
    """Wrapper around the Google GenAI client for classifying helpdesk requests.

        Builds a structured batch prompt from the Service Catalog and requests,
        sends it to the LLM, and maps the JSON response into LLMClassificationResult
        objects keyed by raw_id.
        """

    def __init__(self, config: LLMConfig) -> None:
        if not config.api_key:
            raise LLMClassificationError("LLM_API_KEY must be configured.")

        self._client = genai.Client(api_key=config.api_key)
        self._model = config.model_name

    def classify_helpdesk_request(self, request: HelpdeskRequest, catalog: ServiceCatalog) -> LLMClassificationResult:
        """Classify a single helpdesk request using the LLM.

            Internally calls classify_batch with a single-element list, then:
            - if request.raw_id is set, returns the matching result by raw_id,
              or raises LLMClassificationError if it is missing from the LLM output;
            - if request.raw_id is empty, logs a warning and returns the first
              available classification result.
            """

        results = self.classify_batch([request], catalog)
        raw_id = (request.raw_id or "").strip()

        if not results:
            raise LLMClassificationError(
                "LLM returned no valid items for single helpdesk request",
            )

        if raw_id:
            if raw_id in results:
                return results[raw_id]
            raise LLMClassificationError(
                f"LLM response missing entry for raw_id={raw_id!r} in single-request call",
            )

        logger.warning(
            "HelpdeskRequest without raw_id; using first LLM result as fallback "
            "for single-request classification",
        )
        return next(iter(results.values()))

    def classify_batch(self,requests: Sequence[HelpdeskRequest], catalog: ServiceCatalog) -> dict[
        str, LLMClassificationResult]:
        """Classify a batch of helpdesk requests using the LLM.

            Builds a prompt from the Service Catalog and the given requests, asks
            the model for JSON output, then validates and converts the 'items' list
            into a dict keyed by raw_id.

            Raises LLMClassificationError on API failures, invalid JSON, missing
            'items', empty results, or when all items are rejected as malformed.
            """

        if not requests:
            return {}

        requests_list: list[HelpdeskRequest] = list(requests)
        catalog_fragment = _catalog_to_prompt_fragment(catalog)
        requests_block = _build_batch(requests_list)

        prompt = LLM_BATCH_PROMPT_TEMPLATE.format(
            catalog=catalog_fragment,
            requests_block=requests_block,
        )

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )
        except Exception as exc:
            logger.error("LLM batch classification call failed: %s", exc)
            raise LLMClassificationError("LLM batch API call failed") from exc

        text = _get_response_text(response)

        try:
            data: dict[str, Any] = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error("LLM batch returned non-JSON output: %r", text[:300])
            raise LLMClassificationError("LLM batch output was not valid JSON") from exc

        items = data.get("items")
        if not isinstance(items, list):
            logger.error("LLM batch JSON missing 'items' list: %r", data)
            raise LLMClassificationError("LLM batch JSON missing 'items' list")

        if not items:
            logger.error("LLM batch JSON contained an empty 'items' list: %r", data)
            raise LLMClassificationError(
                "LLM batch JSON contained an empty 'items' list",
            )

        results: dict[str, LLMClassificationResult] = {}

        # log if skip malformed items to catch format drift early
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                logger.warning(
                    "Skipping non-dict item at index %d in LLM batch JSON: %r",
                    index,
                    item,
                )
                continue

            raw_id_raw = item.get("raw_id")
            raw_id = normalize_str_or_none(raw_id_raw)
            if not raw_id:
                logger.warning(
                    "Skipping LLM item without valid 'raw_id' at index %d: %r",
                    index,
                    item,
                )
                continue

            result = LLMClassificationResult(
                request_category=normalize_str_or_none(item.get("request_category")),
                request_type=normalize_str_or_none(item.get("request_type")),
                sla_unit=normalize_str_or_none(item.get("sla_unit")),
                sla_value=normalize_int_or_none(item.get("sla_value")),
            )
            results[raw_id] = result

        # if all items were rejected, treat it as a format error
        if not results:
            logger.error(
                "LLM batch JSON contained %d item(s) but no valid results after "
                "validation. Data: %r",
                len(items),
                items,
            )
            raise LLMClassificationError(
                "LLM batch JSON contained no valid items (all missing or invalid 'raw_id')",
            )

        logger.debug("LLM batch classification produced %d items", len(results))
        return results

def _catalog_to_prompt_fragment(catalog: ServiceCatalog) -> str:
    """Render the Service Catalog into a simple text fragment for the prompt."""

    lines: list[str] = []
    for category in catalog.categories:
        for req_type in category.requests:
            sla = req_type.sla
            lines.append(
                f"- Category: {category.name} | "
                f"Request Type: {req_type.name} | "
                f"SLA: {sla.value} {sla.unit}"
            )
    return "\n".join(lines)

def _build_batch(requests: list[HelpdeskRequest]) -> str:
    """Build the text block describing all requests for the LLM prompt."""

    parts: list[str] = []
    for req in requests:
        raw_payload_str = json.dumps(req.raw_payload or {}, ensure_ascii=False)
        parts.append(
            f"ID: {req.raw_id or ''}\n"
            f"Short description: {req.short_description or ''}\n"
            f"Raw payload JSON: {raw_payload_str}"
        )
    return "\n\n---\n\n".join(parts)

def _get_response_text(response: Any) -> str:
    """Extract non-empty text from the LLM response or raise an error."""

    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text
    raise LLMClassificationError("LLM response contained no text")