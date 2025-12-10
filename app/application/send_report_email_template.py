from __future__ import annotations


def build_email_body(
    codebase_url: str,
    candidate_name: str,
) -> str:
    return (
        "Hi,\n\n"
        "Please find attached the classified helpdesk requests report.\n\n"
        f"Codebase: {codebase_url}\n\n"
        "Best regards,\n"
        f"{candidate_name}\n"
    )