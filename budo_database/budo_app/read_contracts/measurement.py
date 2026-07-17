from dataclasses import dataclass
from time import perf_counter

from django.db import DEFAULT_DB_ALIAS, connections
from django.test.utils import CaptureQueriesContext


# Frozen characterization captured before /api/app-data/ was removed. See
# docs/performance/2026-07-17-legacy-app-data-baseline.md.
RECORDED_LEGACY_REALISTIC_RESPONSE_BYTES = 125_495


@dataclass(frozen=True)
class HttpMeasurement:
    response: object
    status_code: int
    response_bytes: int
    query_count: int
    sql_time_ms: float


def measure_http_get(client, url, *, database=DEFAULT_DB_ALIAS, **request):
    """Measure one Django HTTP GET without imposing a wall-clock assertion."""
    connection = connections[database]
    sql_timer = _SqlTimer()
    with connection.execute_wrapper(sql_timer):
        with CaptureQueriesContext(connection) as queries:
            response = client.get(url, **request)
            if hasattr(response, "render") and not response.is_rendered:
                response.render()

    return HttpMeasurement(
        response=response,
        status_code=response.status_code,
        response_bytes=len(response.content),
        query_count=len(queries),
        sql_time_ms=round(sql_timer.total_seconds * 1000, 3),
    )


class _SqlTimer:
    def __init__(self):
        self.total_seconds = 0

    def __call__(self, execute, sql, params, many, context):
        started = perf_counter()
        try:
            return execute(sql, params, many, context)
        finally:
            self.total_seconds += perf_counter() - started


class QueryBudgetAssertions:
    """Reusable upper-bound and fixture-scaling query assertions."""

    def assertQueryCountAtMost(self, measurement, maximum):
        if measurement.query_count > maximum:
            self.fail(
                f"Expected at most {maximum} queries, "
                f"measured {measurement.query_count}."
            )

    def assertQueryGrowthAtMost(self, smaller, larger, maximum_growth):
        growth = larger.query_count - smaller.query_count
        if growth > maximum_growth:
            self.fail(
                f"Expected query growth of at most {maximum_growth}, "
                f"measured {growth} ({smaller.query_count} -> "
                f"{larger.query_count})."
            )
