from __future__ import annotations
import logging
from app.infrastructure.helpdesk_client import HelpdeskAPIError
from app.application.helpdesk_services import HelpdeskService
from app.infrastructure.config_loader import load_email_config
from app.infrastructure.service_catalog_client import ServiceCatalogClient, ServiceCatalogError
from app.domain.helpdesk import HelpdeskRequest
from app.domain.service_catalog import ServiceCatalog
from app.infrastructure.email_sender import SMTPSender
from app.application.send_report import send_report
from datetime import datetime
from pathlib import Path
from app.infrastructure.report_log import SQLiteReportLog
from typing import Iterable, Sequence


logger = logging.getLogger(__name__)

def _load_helpdesk_requests(service: HelpdeskService) -> Sequence[HelpdeskRequest]:
    """Load helpdesk requests via the given service.
        Logs the number of successfully loaded requests.
        On failure (when the underlying Helpdesk client raises HelpdeskAPIError),
        logs an error and terminates the process with SystemExit(1).
        """

    try:
        requests_ = service.load_helpdesk_requests()
    except HelpdeskAPIError as exc:
        logger.error("Failed to load helpdesk requests: %s", exc)
        raise SystemExit(1) from exc

    logger.info("Successfully loaded %d requests", len(requests_))
    return requests_

def _load_service_catalog(catalog_client: ServiceCatalogClient) -> ServiceCatalog:
    """Load the Service Catalog from the given client.
        Logs the number of categories in the loaded catalog.
        On failure (when the underlying client raises ServiceCatalogError),
        logs an error and terminates the process with SystemExit(1).
        """

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

def _log_sample_requests(requests_: Sequence[HelpdeskRequest], limit: int = 5) -> None:
    """Log a small sample of loaded requests for debugging.
        Logs up to ``limit`` requests, showing their raw IDs and short descriptions.
        This is intended to give quick visibility into the incoming data shape.
        """

    for req in requests_[:limit]:
        logger.info(
            "[part 1] Request ID=%s short_description=%r",
            req.raw_id,
            req.short_description,
        )

def _send_report(
    report_path: list[Path],
    report_log: SQLiteReportLog,
) -> None:
    """Send one or more report files via email and mark them as sent.

        - Loads email configuration and constructs an SMTP sender.
        - Validates that all report paths exist on disk.
        - Sends a report email using the shared send_report application helper.
        - Marks each successfully sent report as 'sent' in the SQLiteReportLog,
          together with the current timestamp.

        If any report file does not exist, logs an error and terminates
        the process with SystemExit(1).
        """

    email_config = load_email_config()
    email_sender = SMTPSender(email_config)

    try:
        attachment_paths = _resolve_report_paths(report_path)
    except FileNotFoundError as exc:
        logger.error(
            "Cannot send report email because an attachment file is missing: %s",
            exc,
        )
        raise SystemExit(1) from exc

    send_report(
        email_sender=email_sender,
        attachment_paths=attachment_paths,
        codebase_url="https://github.com/Steaxy/automated_ticket_attribution",
        candidate_name=email_config.candidate_name,
    )

    # mark the resolved paths as sent
    now = datetime.now()
    for report in attachment_paths:
        report_log.mark_sent(report, created_at=now)
        logger.info(
            "Classified report %s marked as sent in log at %s",
            report.name,
            now.isoformat(sep=" ", timespec="seconds"),
        )

def _collect_unsent_reports(
    project_root: Path,
    report_log: SQLiteReportLog,
    explicit_report: str | None,
) -> tuple[list[Path], Path | None]:
    """Collect report files that have not yet been logged as sent.

        If ``explicit_report`` is provided, only that path is considered and
        returned (if it has no sent record in the log). Otherwise, all ``*.xlsx``
        files inside ``project_root / "output"`` are scanned and sorted by
        modification time (oldest first).

        Returns a tuple ``(unsent_report_paths, explicit_report_path)`` where:
          - ``unsent_report_paths`` is the list of report paths that do not have a
            corresponding 'sent' record in the log.
          - ``explicit_report_path`` is the resolved Path for the explicitly
            provided report, or ``None`` when auto-discovery is used.
        """

    if explicit_report is not None:
        candidates = [Path(explicit_report).resolve()]
        explicit_report_path: Path | None = candidates[0]
    else:
        output_dir = project_root / "output"
        if not output_dir.is_dir():
            return [], None

        candidates = sorted(
            output_dir.glob("*.xlsx"),
            key=lambda p: p.stat().st_mtime,
        )
        explicit_report_path = None

    unsent_report_paths: list[Path] = []
    for candidate in candidates:
        record = report_log.get_record(candidate)
        if record is None:
            unsent_report_paths.append(candidate)
        else:
            logger.info(
                "Classified report %s was already sent at %s",
                candidate.name,
                record.created_at.isoformat(sep=" ", timespec="seconds"),
            )

    return unsent_report_paths, explicit_report_path

def _resolve_report_paths(report_paths: Iterable[Path]) -> list[Path]:
    """Validate that all given report paths exist and return their absolute paths.
        Raises FileNotFoundError if any of the paths does not point to an existing
        file. All returned paths are resolved to absolute Paths.
    """

    paths: list[Path] = []
    for path in report_paths:
        if not path.is_file():
            raise FileNotFoundError(f"Report file does not exist: {path}")
        paths.append(path.resolve())
    return paths