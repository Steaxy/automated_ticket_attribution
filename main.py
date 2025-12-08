import logging
from app.infrastructure.helpdesk_client import HelpdeskClient, HelpdeskAPIError
from app.application.helpdesk_services import HelpdeskService
from app.config import (
    load_helpdesk_config,
    load_service_catalog_config,
)
from app.infrastructure.service_catalog_client import ServiceCatalogClient, ServiceCatalogError


logger = logging.getLogger(__name__)

def logging_conf() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )


def main() -> None:
    logging_conf()

    config = load_helpdesk_config()
    client = HelpdeskClient(config)

    # raw data check
    # raw = client.fetch_raw()
    # import pprint
    # pprint.pp(raw)
    # return

    service = HelpdeskService(client)

    catalog_config = load_service_catalog_config()
    catalog_client = ServiceCatalogClient(catalog_config)

    # helpdesk requests
    try:
        requests_ = service.load_helpdesk_requests()
    except HelpdeskAPIError as exc:
        logging.getLogger(__name__).error("Failed to load helpdesk requests: %s", exc)
        raise SystemExit(1) from exc
    logger.info("Successfully loaded %d requests", len(requests_))

    # service catalog
    try:
        service_catalog = catalog_client.fetch_catalog()
    except ServiceCatalogError as exc:
        logger.error("Failed to load Service Catalog: %s", exc)
        raise SystemExit(1) from exc
    logger.info(
        "Service Catalog loaded: %d categories",
        len(service_catalog.categories),
    )

    # print first few items
    for req in requests_[:5]:
        logger.info("Request ID=%s short_description=%r", req.raw_id, req.short_description)


if __name__ == "__main__":
    main()