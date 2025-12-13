from __future__ import annotations
import logging
from typing import Any
import requests
from requests import HTTPError, RequestException
from app.config import HelpdeskAPIConfig
from app.domain.helpdesk import HelpdeskRequest
import time
from app.application.dto.fetched_helpdesk_request import FetchedHelpdeskRequest


logger = logging.getLogger(__name__)

class HelpdeskAPIError(RuntimeError):
    """Raised when Helpdesk API cannot be called or its response cannot be parsed/validated."""

class HelpdeskClient:
    """HTTP client for fetching helpdesk requests from the Helpdesk API.
        Calls the configured endpoint with credentials, parses the JSON response,
        extracts request items, and returns them as `FetchedHelpdeskRequest`
        (domain request + raw payload envelope).
        """

    def __init__(
        self,
        config: HelpdeskAPIConfig,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> None:
        self._config = config
        self._session = requests.Session()
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor

    def _post_json(self) -> Any:
        """Call the Helpdesk API and return the parsed JSON body.
            Retries on HTTP/network failures with exponential backoff.
            Raises:
                HelpdeskAPIError: on request failures after retries or invalid JSON.
            """

        payload = {
            "api_key": self._config.api_key,
            "api_secret": self._config.api_secret,
        }

        # retry POST with exponential backoff on HTTP/network errors
        response: requests.Response | None = None
        last_exc: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = self._session.post(
                    self._config.url,
                    json=payload,
                    timeout=self._config.timeout_seconds,
                )
                response.raise_for_status()
                break
            except (HTTPError, RequestException) as exc:
                last_exc = exc
                if attempt == self._max_retries:
                    msg = (
                        f"Error calling Helpdesk API after {self._max_retries} "
                        f"attempts: {exc}"
                    )
                    logger.error(msg)
                    raise HelpdeskAPIError(msg) from exc

                sleep_seconds = self._backoff_factor * (2 ** (attempt - 1))
                logger.warning(
                    "Helpdesk API call failed on attempt %d/%d: %s; "
                    "retrying in %.1f seconds",
                    attempt,
                    self._max_retries,
                    exc,
                    sleep_seconds,
                )
                time.sleep(sleep_seconds)

        if response is None:
            msg = "Helpdesk API call failed without a response object"
            logger.error(msg)
            if last_exc is not None:
                raise HelpdeskAPIError(msg) from last_exc
            raise HelpdeskAPIError(msg)

        try:
            return response.json()
        except ValueError as exc:
            msg = "Failed to parse Helpdesk API response as JSON"
            logger.error(msg)
            raise HelpdeskAPIError(msg) from exc

    def fetch_raw(self) -> Any:
        """Fetch the raw JSON response from the Helpdesk API."""
        return self._post_json()

    def fetch_requests(self) -> list[FetchedHelpdeskRequest]:
        """Fetch helpdesk requests and map them into domain + raw envelope."""

        data = self._post_json()
        logger.info(
            "Raw Helpdesk API response keys: %s",
            list(data.keys()) if isinstance(data, dict) else type(data),
        )

        items = self._extract_items(data)

        result: list[FetchedHelpdeskRequest] = []
        for item in items:
            id = _normalize_optional_str(item.get("id") or item.get("ticket_id"))
            short_description = _normalize_optional_str(item.get("short_description") or item.get("subject"))

            long_description = _normalize_optional_str(
                item.get("long_description") or item.get("description") or item.get("body")
            )

            request_category = _normalize_optional_str(item.get("request_category"))
            request_type = _normalize_optional_str(item.get("request_type"))

            sla_payload = item.get("sla")
            sla_unit: str | None = None
            sla_value: int | None = None
            if isinstance(sla_payload, dict):
                sla_unit = _normalize_optional_str(sla_payload.get("unit"))
                sla_value = _normalize_optional_int(sla_payload.get("value"))

            domain_req = HelpdeskRequest(
                id=id,
                short_description=short_description,
                long_description=long_description,
                request_category=request_category,
                request_type=request_type,
                sla_unit=sla_unit,
                sla_value=sla_value,
            )

            result.append(
                FetchedHelpdeskRequest(
                    request=domain_req,
                    raw_payload=item,
                )
            )

        logger.info("Fetched %d helpdesk requests", len(result))
        return result

    def _extract_items(self, data: Any) -> list[dict[str, Any]]:
        """Extract a list of request dicts from the Helpdesk API JSON.
            Supported shapes:
            - top-level list of dicts
            - top-level dict with `data` as list of dicts
            - top-level dict with `data.requests` as list of dicts
            Raises:
                HelpdeskAPIError: if no supported shape matches.
            """

        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]

        if isinstance(data, dict):
            payload = data.get("data", data)

            if isinstance(payload, list):
                return [item for item in payload if isinstance(item, dict)]

            if isinstance(payload, dict):
                items_payload = payload.get("requests")
                if isinstance(items_payload, list):
                    return [item for item in items_payload if isinstance(item, dict)]

                logger.error(
                    "Helpdesk API 'data' dict has no 'requests' list. data keys=%s, payload keys=%s",
                    list(data.keys()),
                    list(payload.keys()),
                )
                raise HelpdeskAPIError(
                    "Unexpected response shape from Helpdesk API: "
                    "'data.requests' key missing or not a list"
                )

            logger.error(
                "Helpdesk API 'data' has unexpected type: %s",
                type(payload).__name__,
            )
            raise HelpdeskAPIError(
                "Unexpected response shape from Helpdesk API: 'data' is not dict or list"
            )

        msg = f"Unexpected response format from Helpdesk API: {type(data).__name__}"
        logger.error(msg)
        raise HelpdeskAPIError(msg)

def _normalize_optional_str(value: Any) -> str | None:
    """Return stripped string or None for empty/whitespace."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_optional_int(value: Any) -> int | None:
    """Return int or None for missing/invalid/zero."""
    if value is None:
        return None
    try:
        # accept "3.0" and 3.0
        if isinstance(value, float):
            number = int(value)
        else:
            number = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return None if number == 0 else number