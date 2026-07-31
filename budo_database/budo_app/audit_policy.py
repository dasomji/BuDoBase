"""Central authorization policy for access to sensitive audit data."""

import logging

from rest_framework.permissions import IsAuthenticated


logger = logging.getLogger(__name__)

VIEW_AUDIT_PERMISSION = "budo_app.view_auditevent"
EXPORT_AUDIT_PERMISSION = "budo_app.export_auditevent"


def _eligible_staff(user):
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
        and getattr(user, "is_staff", False)
    )


def can_view_audit(user):
    return bool(
        _eligible_staff(user)
        and user.has_perm(VIEW_AUDIT_PERMISSION)
    )


def can_export_audit(user):
    return bool(
        can_view_audit(user)
        and user.has_perm(EXPORT_AUDIT_PERMISSION)
    )


def log_audit_denial(*, user, endpoint_kind, reason_code):
    endpoint = (
        endpoint_kind
        if endpoint_kind in {"list", "detail", "export"}
        else "unknown"
    )
    reason = (
        reason_code
        if reason_code in {
            "authentication_required",
            "forbidden",
            "scope_unavailable",
        }
        else "forbidden"
    )
    actor_id = getattr(user, "id", None)
    logger.warning(
        "audit_access_denied actor_id=%s endpoint=%s reason=%s",
        actor_id,
        endpoint,
        reason,
    )


class AuditAwareIsAuthenticated(IsAuthenticated):
    """Keep generic route auth behavior and log anonymous audit-list denial."""

    def has_permission(self, request, view):
        allowed = super().has_permission(request, view)
        if not allowed and getattr(view, "kwargs", {}).get(
            "contract_key"
        ) == "audit-events":
            log_audit_denial(
                user=request.user,
                endpoint_kind="list",
                reason_code="authentication_required",
            )
        return allowed


class AuditExportIsAuthenticated(IsAuthenticated):
    """Log anonymous export denial before the export view is entered."""

    def has_permission(self, request, view):
        allowed = super().has_permission(request, view)
        if not allowed:
            log_audit_denial(
                user=request.user,
                endpoint_kind="export",
                reason_code="authentication_required",
            )
        return allowed


class AuditDetailIsAuthenticated(IsAuthenticated):
    """Log anonymous detail denial before the detail view is entered."""

    def has_permission(self, request, view):
        allowed = super().has_permission(request, view)
        if not allowed:
            log_audit_denial(
                user=request.user,
                endpoint_kind="detail",
                reason_code="authentication_required",
            )
        return allowed
