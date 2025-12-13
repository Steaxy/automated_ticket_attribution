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
from app.shared.normalization import normalize_str_or_none
from app.infrastructure.llm_classifier_prompt import LLM_BATCH_PROMPT_TEMPLATE
from typing import Sequence
import time


logger = logging.getLogger(__name__)

class LLMClassifier:
    """Wrapper around the Google GenAI client for classifying helpdesk requests.

        Builds a structured batch prompt from the Service Catalog and requests,
        sends it to the LLM, and maps the JSON response into LLMClassificationResult
        objects keyed by id.
        """

    def __init__(self, config: LLMConfig) -> None:
        if not config.api_key:
            raise LLMClassificationError("LLM_API_KEY must be configured.")

        self._config = config
        self._client = genai.Client(api_key=config.api_key)
        self._model = config.model_name
        self._delay_between_batches: float = config.delay_between_batches

    def classify_helpdesk_request(self, request: HelpdeskRequest, catalog: ServiceCatalog) -> LLMClassificationResult:
        """Classify a single helpdesk request using the LLM.

            Internally calls classify_batch with a single-element list, then:
            - if request.id is set, returns the matching result by id,
              or raises LLMClassificationError if it is missing from the LLM output;
            - if request.id is empty, logs a warning and returns the first
              available classification result.
            """

        results = self.classify_batch([request], catalog)
        id = (request.id or "").strip()

        if not results:
            raise LLMClassificationError(
                "LLM returned no valid items for single helpdesk request",
            )

        if id:
            if id in results:
                return results[id]
            raise LLMClassificationError(
                f"LLM response missing entry for id={id!r} in single-request call",
            )

        logger.warning(
            "HelpdeskRequest without id; using first LLM result as fallback "
            "for single-request classification",
        )
        return next(iter(results.values()))

    def classify_batch(self,requests: Sequence[HelpdeskRequest], catalog: ServiceCatalog) -> dict[
        str, LLMClassificationResult]:
        """Classify a batch of helpdesk requests using the LLM.

            Builds a prompt from the Service Catalog and the given requests, asks
            the model for JSON output, then validates and converts the 'items' list
            into a dict keyed by id.

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
                    temperature=self._config.temperature,
                    top_p=self._config.top_p,
                    top_k=self._config.top_k,
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

            id_raw = item.get("id")
            id = normalize_str_or_none(id_raw)
            if not id:
                logger.warning(
                    "Skipping LLM item without valid 'id' at index %d: %r",
                    index,
                    item,
                )
                continue

            # warn if model returned SLA fields (must be ignored; SLA comes from Service Catalog)
            raw_sla_unit = item.get("sla_unit")
            raw_sla_value = item.get("sla_value")
            if raw_sla_unit is not None or raw_sla_value is not None:
                logger.warning(
                    "LLM returned SLA fields for request %s at index %d (sla_unit=%r, sla_value=%r). "
                    "Ignoring them; SLA is derived from Service Catalog.",
                    id,
                    index,
                    raw_sla_unit,
                    raw_sla_value,
                )

            result = LLMClassificationResult(
                request_category=normalize_str_or_none(item.get("request_category")),
                request_type=normalize_str_or_none(item.get("request_type")),
            )
            results[id] = result

        # if all items were rejected, treat it as a format error
        if not results:
            logger.error(
                "LLM batch JSON contained %d item(s) but no valid results after "
                "validation. Data: %r",
                len(items),
                items,
            )
            raise LLMClassificationError(
                "LLM batch JSON contained no valid items (all missing or invalid 'id')",
            )

        logger.debug("LLM batch classification produced %d items", len(results))

        if self._delay_between_batches > 0:
            logger.debug(
                "Sleeping %.2f seconds between LLM batches",
                self._delay_between_batches,
            )
            time.sleep(self._delay_between_batches)

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
        parts.append(
            f"ID: {req.id or ''}\n"
            f"Short description: {req.short_description or ''}\n"
            f"Long description: {req.long_description or ''}\n"
            f"Current request_category: {req.request_category or ''}\n"
            f"Current request_type: {req.request_type or ''}\n"
        )
    return "\n\n---\n\n".join(parts)

def _get_response_text(response: Any) -> str:
    """Extract non-empty text from the LLM response or raise an error."""

    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text
    raise LLMClassificationError("LLM response contained no text")