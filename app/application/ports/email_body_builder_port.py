from __future__ import annotations
from typing import Protocol


class EmailBodyBuilder(Protocol):
    def build(self, codebase_url: str, candidate_name: str) -> tuple[str, str]:
        ...