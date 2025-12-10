from __future__ import annotations
import logging
from pathlib import Path
from typing import Protocol
from app.application.send_report_email_template import build_email_body


logger = logging.getLogger(__name__)

class ReportEmailSender(Protocol):
    def send_report_email(
            self,
            subject: str,
            body: str,
            attachments: list[Path]
    ) -> None:
        ...

def send_report(
    email_sender: ReportEmailSender,
    reports: list[str],
    codebase_url: str,
    candidate_name: str,
) -> None:
    # convert string paths to Path objects
    attachment_paths: list[Path] = []
    for report_path in reports:
        path = Path(report_path)
        if not path.is_file():
            raise FileNotFoundError(f"Report file does not exist: {path}")
        attachment_paths.append(path)

    subject = f"Automation Engineer interview - technical task - {candidate_name}"

    body = build_email_body(
        codebase_url=codebase_url,
        candidate_name=candidate_name,
    )

    logger.info(
        "Sending classified report %r with %d attachment(s)",
        subject,
        len(attachment_paths),
    )

    email_sender.send_report_email(subject, body, attachment_paths)