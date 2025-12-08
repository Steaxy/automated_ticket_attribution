from typing import Any
from unittest.mock import Mock
import builtins
import pytest
from requests import HTTPError
from app.config import ServiceCatalogConfig
from app.domain.service_catalog import ServiceCatalog
from app.infrastructure.service_catalog_client import (
    ServiceCatalogClient,
    ServiceCatalogError,
)


def _make_client_with_mock_session(raw_text: str) -> ServiceCatalogClient:
    config = ServiceCatalogConfig(
        url="https://example.com/service-catalog",
        timeout_seconds=5.0,
    )

    client = ServiceCatalogClient(config)

    mock_session = Mock()
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.text = raw_text

    mock_session.get = Mock(return_value=mock_response)
    client._session = mock_session                              # type: ignore[attr-defined]

    return client

def test_fetch_catalog_happy_path() -> None:
    yaml_text = """
service_catalog:
  catalog:
    categories:
      - name: "Access Management"
        requests:
          - name: "Reset Okta password"
            sla:
              unit: "hours"
              value: "4"
"""

    client = _make_client_with_mock_session(yaml_text)

    catalog: ServiceCatalog = client.fetch_catalog()

    assert len(catalog.categories) == 1
    cat = catalog.categories[0]
    assert cat.name == "Access Management"
    assert len(cat.requests) == 1

    req = cat.requests[0]
    assert req.name == "Reset Okta password"
    assert req.sla.unit == "hours"
    # value must be converted to int
    assert req.sla.value == 4

def test_fetch_catalog_unexpected_shape_raises() -> None:
    yaml_text = """
service_catalog:
  catalog:
    not_categories: []
"""

    client = _make_client_with_mock_session(yaml_text)

    with pytest.raises(ServiceCatalogError):
        _ = client.fetch_catalog()


def test_fetch_catalog_mapping_error_raises() -> None:
    yaml_text = """
service_catalog:
  catalog:
    categories:
      - name: "Access Management"
        requests:
          - name: "Reset Okta password"
"""

    client = _make_client_with_mock_session(yaml_text)

    with pytest.raises(ServiceCatalogError):
        _ = client.fetch_catalog()

def test_http_error_is_wrapped_in_service_catalog_error() -> None:
    config = ServiceCatalogConfig(
        url="https://example.com/service-catalog",
        timeout_seconds=5.0,
    )

    client = ServiceCatalogClient(config)

    mock_session = Mock()
    mock_response = Mock()

    mock_response.raise_for_status.side_effect = HTTPError("500 server error")
    mock_session.get.return_value = mock_response

    client._session = mock_session                                                  # type: ignore[attr-defined]

    with pytest.raises(ServiceCatalogError):
        _ = client.fetch_catalog()

def test_parse_yaml_import_error_is_wrapped_in_service_catalog_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = ServiceCatalogConfig(
        url="https://example.com/service-catalog",
        timeout_seconds=5.0,
    )
    client = ServiceCatalogClient(config)

    original_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "yaml":
            raise ImportError("PyYAML not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    with pytest.raises(ServiceCatalogError):
        _ = client._parse_yaml("service_catalog: {}")                               # type: ignore[attr-defined]


def test_parse_yaml_error_is_wrapped_in_service_catalog_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import yaml                                                                     # type: ignore[import]

    config = ServiceCatalogConfig(
        url="https://example.com/service-catalog",
        timeout_seconds=5.0,
    )
    client = ServiceCatalogClient(config)

    def fake_safe_load(_: str) -> Any:
        raise yaml.YAMLError("bad yaml")                                            # type: ignore[attr-defined]

    monkeypatch.setattr("yaml.safe_load", fake_safe_load)

    with pytest.raises(ServiceCatalogError):
        _ = client._parse_yaml(":::")                                               # type: ignore[attr-defined]