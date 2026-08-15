def documentation(_request):
    """Return the authenticated empty contract for static in-app guidance."""
    return {}


CONTRACTS = {
    "documentation": documentation,
}
