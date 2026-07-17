from dataclasses import dataclass
from typing import Callable

from .domains import (
    allocation,
    attendance,
    dashboard,
    focuses,
    kids,
    kitchen,
    maintenance,
    people,
    places,
    reports,
)


ContractBuilder = Callable[[object], dict]


@dataclass(frozen=True)
class RouteContract:
    key: str
    domain: str
    builder: ContractBuilder


DOMAIN_CONTRACTS = {
    "allocation": allocation.CONTRACTS,
    "attendance": attendance.CONTRACTS,
    "dashboard": dashboard.CONTRACTS,
    "focuses": focuses.CONTRACTS,
    "kids": kids.CONTRACTS,
    "kitchen": kitchen.CONTRACTS,
    "maintenance": maintenance.CONTRACTS,
    "people": people.CONTRACTS,
    "places": places.CONTRACTS,
    "reports": reports.CONTRACTS,
}


def _build_registry():
    registry = {}
    for domain, contracts in DOMAIN_CONTRACTS.items():
        for key, builder in contracts.items():
            if key in registry:
                raise RuntimeError(f"Duplicate route contract key: {key}")
            registry[key] = RouteContract(
                key=key,
                domain=domain,
                builder=builder,
            )
    return registry


ROUTE_CONTRACTS = _build_registry()


def get_contract(key):
    return ROUTE_CONTRACTS.get(key)
