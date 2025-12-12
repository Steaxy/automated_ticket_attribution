from __future__ import annotations
from html import escape
from importlib import resources
from app.application.ports.email_body_builder_port import EmailBodyBuilder


class EmailTemplateError(RuntimeError):
    pass

TEMPLATES_PACKAGE = "app.infrastructure.email_templates"

def _load_template(filename: str) -> str:
    try:
        return resources.files(TEMPLATES_PACKAGE).joinpath(filename).read_text(
            encoding="utf-8",
        )
    except OSError as exc:
        raise EmailTemplateError(f"Failed to load email template: {filename}") from exc

class TemplateEmailBodyBuilder(EmailBodyBuilder):
    def build(self, codebase_url: str, candidate_name: str) -> tuple[str, str]:
        text_template = _load_template("report_helpdesk_email.txt")
        html_template = _load_template("report_helpdesk_email.html")

        text_body = text_template.format(
            codebase_url=codebase_url,
            candidate_name=candidate_name,
        )
        html_body = html_template.format(
            codebase_url=escape(codebase_url),
            candidate_name=escape(candidate_name),
        )
        return text_body, html_body