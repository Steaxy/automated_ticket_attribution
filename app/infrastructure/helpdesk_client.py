from __future__ import annotations
import logging
from typing import Any, Dict, List
import requests
from requests import HTTPError, RequestException
from app.config import HelpdeskAPIConfig
from app.domain.models import HelpdeskRequest


logger = logging.getLogger(__name__)

class HelpdeskAPIError(RuntimeError):
    pass


class HelpdeskClient:
    def __init__(self, config: HelpdeskAPIConfig) -> None:
        self._config = config
        self._session = requests.Session()

    def _post_json(self) -> Any:
        payload = {
            "api_key": self._config.api_key,
            "api_secret": self._config.api_secret,
        }

        try:
            response = self._session.post(
                self._config.url,
                json=payload,
                timeout=self._config.timeout_seconds,
            )
            response.raise_for_status()
        except (HTTPError, RequestException) as exc:
            msg = f"Error calling Helpdesk API: {exc}"
            logger.error(msg)
            raise HelpdeskAPIError(msg) from exc

        try:
            return response.json()
        except ValueError as exc:
            msg = "Failed to parse Helpdesk API response as JSON"
            logger.error(msg)
            raise HelpdeskAPIError(msg) from exc

    def fetch_raw(self) -> Any:
        return self._post_json()

    def fetch_requests(self) -> List[HelpdeskRequest]:
        data = self._post_json()
        logger.info(
            "Raw Helpdesk API response keys: %s",
            list(data.keys()) if isinstance(data, dict) else type(data),
        )

        items = self._extract_items(data)

        requests_list: List[HelpdeskRequest] = []
        for item in items:
            if not isinstance(item, dict):
                logger.warning("Skipping non-object item in response: %r", item)
                continue

            raw_id = _safe_str(item.get("id") or item.get("ticket_id"))
            short_description = _safe_str(
                item.get("short_description") or item.get("subject")
            )

            requests_list.append(
                HelpdeskRequest(
                    raw_id=raw_id,
                    short_description=short_description,
                    raw_payload=item,
                )
            )

        logger.info("Fetched %d helpdesk requests", len(requests_list))
        return requests_list

    def _extract_items(self, data: Any) -> List[Dict[str, Any]]:
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]

        if isinstance(data, dict):
            payload = data.get("data", data)

            if isinstance(payload, list):
                return [item for item in payload if isinstance(item, dict)]

            if isinstance(payload, dict):
                requests = payload.get("requests")
                if isinstance(requests, list):
                    return [item for item in requests if isinstance(item, dict)]

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

def _safe_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)