from dataclasses import dataclass
import os
from dotenv import load_dotenv


@dataclass(frozen=True)
class HelpdeskAPIConfig:
    url: str
    api_key: str
    api_secret: str
    timeout_seconds: float = 10.0


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required but not set")
    return value


def load_helpdesk_config() -> HelpdeskAPIConfig:
    load_dotenv()

    url = _get_required_env("HELPDESK_API_URL")
    api_key = _get_required_env("HELPDESK_API_KEY")
    api_secret = _get_required_env("HELPDESK_API_SECRET")

    return HelpdeskAPIConfig(
        url=url,
        api_key=api_key,
        api_secret=api_secret,
        timeout_seconds=10.0,
    )