from __future__ import annotations
import logging
from pathlib import Path
from typing import Protocol


logger = logging.getLogger(__name__)

class ReportEmailSender(Protocol):
    def send_report_email(self, subject: str, body: str, attachment_path: Path) -> None:
        ...

def send_classified_requests_report(email_sender: ReportEmailSender, report_path: str, codebase_url: str, candidate_name: str) -> None:
    path = Path(report_path)

    if not path.is_file():
        raise FileNotFoundError(f"Report file does not exist: {path}")

    subject = f"Automation Engineer interview - technical task - {candidate_name}"

    body = (
        "Hi,\n\n"
        "Please find attached the classified helpdesk requests report.\n\n"
        f"Codebase: {codebase_url}\n\n"
        "Best regards,\n"
        f"{candidate_name}\n"
    )

    logger.info("Sending classified report %r", subject)
    email_sender.send_report_email(subject=subject, body=body, attachment_path=path)