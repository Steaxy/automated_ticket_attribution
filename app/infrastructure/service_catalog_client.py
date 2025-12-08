from __future__ import annotations
import logging
from typing import Any, List
import requests
from requests import HTTPError, RequestException
from app.config import ServiceCatalogConfig
from app.domain.service_catalog import SLA, ServiceRequestType, ServiceCategory, ServiceCatalog


logger = logging.getLogger(__name__)

class ServiceCatalogError(RuntimeError):
    """Raised when the Service Catalog cannot be retrieved, parsed, or validated."""

class ServiceCatalogClient:
    def __init__(self, config: ServiceCatalogConfig) -> None:
        self._config = config
        self._session = requests.Session()

    def fetch_catalog(self) -> ServiceCatalog:
        text = self._download_text()
        data = self._parse_yaml(text)

        try:
            categories_raw = data["service_catalog"]["catalog"]["categories"]
        except (TypeError, KeyError) as exc:
            msg = (
                "Unexpected Service Catalog shape; "
                "expected 'service_catalog.catalog.categories'"
            )
            logger.error("%s: %s", msg, exc)
            raise ServiceCatalogError(msg) from exc

        try:
            categories: List[ServiceCategory] = []
            for cat in categories_raw:
                name = cat["name"]
                requests_raw = cat["requests"]

                requests = [
                    ServiceRequestType(
                        name=req["name"],
                        sla=SLA(
                            unit=req["sla"]["unit"],
                            value=int(req["sla"]["value"]),
                        ),
                    )
                    for req in requests_raw
                ]

                categories.append(ServiceCategory(name=name, requests=requests))
        except (KeyError, TypeError, ValueError) as exc:
            msg = "Failed to map Service Catalog to domain models"
            logger.error("%s: %s", msg, exc)
            raise ServiceCatalogError(msg) from exc

        catalog = ServiceCatalog(categories=categories)
        logger.info(
            "Loaded Service Catalog: %d categories, %d total request types",
            len(catalog.categories),
            sum(len(c.requests) for c in catalog.categories),
        )
        return catalog

    def _download_text(self) -> str:
        try:
            response = self._session.get(
                self._config.url,
                timeout=self._config.timeout_seconds,
            )
            response.raise_for_status()
        except (HTTPError, RequestException) as exc:
            msg = f"Error calling Service Catalog endpoint: {exc}"
            logger.error(msg)
            raise ServiceCatalogError(msg) from exc

        text = response.text
        logger.debug("Raw Service Catalog response length=%d", len(text))
        return text

    def _parse_yaml(self, text: str) -> Any:
        try:
            import yaml
        except ImportError as exc:
            msg = "PyYAML is required to parse the Service Catalog"
            logger.error(msg)
            raise ServiceCatalogError(msg) from exc

        try:
            return yaml.safe_load(text)
        except yaml.YAMLError as exc:
            msg = "Failed to parse Service Catalog YAML"
            logger.error(msg)
            raise ServiceCatalogError(msg) from exc