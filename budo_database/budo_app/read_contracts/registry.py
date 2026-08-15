from dataclasses import dataclass
from typing import Callable

from .domains import (
    allocation,
    audit,
    attendance,
    dashboard,
    documentation,
    focuses,
    happy_cleaning,
    kid_edit,
    kids,
    kitchen,
    maintenance,
    memberships,
    places,
    profiles,
    reports,
)


ContractBuilder = Callable[[object], dict]


@dataclass(frozen=True)
class RouteContract:
    key: str
    domain: str
    builder: ContractBuilder
    cache_control: str | None = None


DOMAIN_CONTRACTS = {
    "allocation": allocation.CONTRACTS,
    "audit": audit.CONTRACTS,
    "attendance": attendance.CONTRACTS,
    "dashboard": dashboard.CONTRACTS,
    "documentation": documentation.CONTRACTS,
    "focuses": focuses.CONTRACTS,
    "happy-cleaning": happy_cleaning.CONTRACTS,
    "kid-edit": kid_edit.CONTRACTS,
    "kids": kids.CONTRACTS,
    "kitchen": kitchen.CONTRACTS,
    "maintenance": maintenance.CONTRACTS,
    "memberships": memberships.CONTRACTS,
    "places": places.CONTRACTS,
    "profiles": profiles.CONTRACTS,
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
                cache_control=(
                    "private, no-store" if key == "kid-edit" else None
                ),
            )
    return registry


ROUTE_CONTRACTS = _build_registry()


def get_contract(key):
    return ROUTE_CONTRACTS.get(key)
