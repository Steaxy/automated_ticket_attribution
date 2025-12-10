from __future__ import annotations
import logging
from app.infrastructure.helpdesk_client import HelpdeskClient, HelpdeskAPIError
from app.application.helpdesk_services import HelpdeskService
from app.config import (
    load_helpdesk_config,
    load_service_catalog_config,
    load_llm_config,
)
from app.infrastructure.service_catalog_client import ServiceCatalogClient, ServiceCatalogError
from app.infrastructure.llm_classifier import LLMClassifier
from app.application.missing_sla import missing_sla
from app.application.classify_requests import classify_requests
from app.domain.helpdesk import HelpdeskRequest
from app.domain.service_catalog import ServiceCatalog
from app.cmd.spinner import Spinner
from app.infrastructure.save_excel import save_excel
from app.infrastructure.email_sender import SMTPSender
from app.application.send_report import send_classified_requests_report
from app.config import load_email_config


logger = logging.getLogger(__name__)

def pipeline(excel_report: str | None = None) -> None:
    if excel_report is None:
        helpdesk_config = load_helpdesk_config()
        client = HelpdeskClient(helpdesk_config)
        service = HelpdeskService(client)

        catalog_config = load_service_catalog_config()
        catalog_client = ServiceCatalogClient(catalog_config)

        # [part 1] fetch helpdesk requests
        requests_ = _load_helpdesk_requests(service)

        # [part 2] fetch service catalog
        service_catalog = _load_service_catalog(catalog_client)

        # [part 3 and 4] classify the requests by LLM
        llm_config = load_llm_config()
        llm = LLMClassifier(llm_config)

        # classify all requests (even if not success by LLM) and log first 3 of them (displaying spinner while requests in LLM in progress)
        with Spinner("Classifying helpdesk requests with LLM"):
            classified_requests = classify_requests(
                llm,
                service_catalog,
                requests_,
                batch_size=llm_config.batch_size,
            )

        # [part 5] build Excel file
        missing_sla(classified_requests, service_catalog)
        excel = save_excel(classified_requests)

        _log_sample_requests(requests_)
    else:
        logger.info(
            "Send existing excel report file %s",
            excel_report,
        )
        excel = excel_report

    # [part 6] send the report to email
    email_config = load_email_config()
    email_sender = SMTPSender(email_config)

    send_classified_requests_report(
        email_sender=email_sender,
        report_path=excel,
        codebase_url="https://github.com/Steaxy/automated_ticket_attribution",
        candidate_name=email_config.candidate_name,
    )

def _load_helpdesk_requests(service: HelpdeskService) -> list[HelpdeskRequest]:
    try:
        requests_ = service.load_helpdesk_requests()
    except HelpdeskAPIError as exc:
        logger.error("Failed to load helpdesk requests: %s", exc)
        raise SystemExit(1) from exc

    logger.info("Successfully loaded %d requests", len(requests_))
    return requests_

def _load_service_catalog(catalog_client: ServiceCatalogClient) -> ServiceCatalog:
    try:
        service_catalog = catalog_client.fetch_catalog()
    except ServiceCatalogError as exc:
        logger.error("Failed to load Service Catalog: %s", exc)
        raise SystemExit(1) from exc

    logger.info(
        "Service Catalog loaded: %d categories",
        len(service_catalog.categories),
    )
    return service_catalog

def _log_sample_requests(requests_: list[HelpdeskRequest], limit: int = 5) -> None:
    for req in requests_[:limit]:
        logger.info(
            "[part 1] Request ID=%s short_description=%r",
            req.raw_id,
            req.short_description,
        )