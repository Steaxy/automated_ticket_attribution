from __future__ import annotations
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class SLA:
    unit: str
    value: int

@dataclass(frozen=True)
class ServiceRequestType:
    name: str
    sla: SLA

@dataclass(frozen=True)
class ServiceCategory:
    name: str
    requests: List[ServiceRequestType]


@dataclass(frozen=True)
class ServiceCatalog:
    categories: List[ServiceCategory]