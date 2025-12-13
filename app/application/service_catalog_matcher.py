from __future__ import annotations
from dataclasses import dataclass
import re
from app.domain.service_catalog import ServiceCatalog


# normalize strings for case-insensitive matching
def _norm(value: str) -> str:
    value = value.strip()
    value = re.sub(r"\s+", " ", value)
    return value.casefold()

@dataclass(frozen=True)
class CatalogMatch:
    request_category: str
    request_type: str

class ServiceCatalogMatcher:
    """Resolves (category, type) coming from LLM into canonical catalog strings."""

    def __init__(self, catalog: ServiceCatalog) -> None:
        # NEW: map normalized pairs -> canonical pair
        pair_map: dict[tuple[str, str], CatalogMatch] = {}

        for category in catalog.categories:
            cat_norm = _norm(category.name)
            for req_type in category.requests:
                type_norm = _norm(req_type.name)
                key = (cat_norm, type_norm)
                canonical = CatalogMatch(
                    request_category=category.name,
                    request_type=req_type.name,
                )

                # protect against collisions (two entries normalize to same key)
                if key in pair_map and pair_map[key] != canonical:
                    pair_map[key] = CatalogMatch(request_category="", request_type="")
                else:
                    pair_map[key] = canonical

        self._pair_map = pair_map

    def resolve(self, request_category: str | None, request_type: str | None) -> CatalogMatch | None:
        if not request_category or not request_type:
            return None

        key = (_norm(request_category), _norm(request_type))
        match = self._pair_map.get(key)
        if not match or not match.request_category:
            return None
        return match