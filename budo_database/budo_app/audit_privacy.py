from django.utils.cache import patch_vary_headers


def apply_audit_privacy_headers(response):
    response["Cache-Control"] = "private, no-store"
    response["Pragma"] = "no-cache"
    response["Referrer-Policy"] = "no-referrer"
    response["X-Content-Type-Options"] = "nosniff"
    patch_vary_headers(response, ("Cookie",))
    return response


class AuditPrivacyHeadersMiddleware:
    """Apply privacy headers only to audit list, detail, and export surfaces."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        match = getattr(request, "resolver_match", None)
        is_list = (
            match is not None
            and match.url_name == "route-data-api"
            and match.kwargs.get("contract_key") == "audit-events"
        )
        is_detail = (
            match is not None and match.url_name == "audit-event-detail-api"
        )
        is_export = (
            match is not None and match.url_name == "audit-export-api"
        )
        if is_list or is_detail or is_export:
            apply_audit_privacy_headers(response)
        return response
