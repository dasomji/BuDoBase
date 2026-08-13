"""Join-request creation and recipient-specific notification delivery.

Notifications are durable and at-least-once. The database claim prevents two live
workers from sending one row concurrently and stale claims are recoverable. Generic
SMTP cannot atomically commit its acceptance with our database update: a process
crash in that narrow interval can cause a retry. Stable Message-ID and idempotency
headers let a capable provider deduplicate that retry, but are not an exactly-once
guarantee for arbitrary SMTP backends.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.utils import timezone

from .audit import AuditEventData, actor_label_for_user, client_ip_from_request, record_audit_event
from .memberships import create_membership, lock_membership_scope
from .models import TurnusJoinRequest, TurnusJoinRequestNotification, TurnusMembership


logger = logging.getLogger(__name__)
CLAIM_LEASE = timedelta(minutes=15)
PENDING_CONSTRAINT = "unique_pending_user_turnus_join_request"

IDENTITY_VERIFICATION_WARNING = (
    "Bitte kontaktiere die Person über einen dir bekannten, unabhängigen Kanal. "
    "Prüfe dabei, dass die E-Mail-Adresse wirklich zu ihr gehört und dass sie "
    "diese Anfrage selbst gestellt hat."
)


class AlreadyTurnusMember(Exception):
    pass


class JoinRequestAlreadyResolved(Exception):
    pass


class JoinRequestDecisionForbidden(Exception):
    pass


def can_decide_join_requests(user, turnus):
    if not getattr(user, "is_authenticated", False):
        return False
    return user.is_superuser or TurnusMembership.objects.filter(
        user=user,
        turnus=turnus,
        functional_role=TurnusMembership.FunctionalRole.LEITUNG,
    ).exists()


def decide_join_request(*, join_request_id, actor, decision, http_request=None):
    """Resolve one pending request and its access/audit effects atomically."""
    if decision not in {"approve", "reject"}:
        raise ValueError("Unknown join-request decision.")

    with transaction.atomic():
        candidate = TurnusJoinRequest.objects.filter(pk=join_request_id).first()
        if candidate is None or not can_decide_join_requests(actor, candidate.turnus):
            # Do not reveal whether a cross-Turnus request exists.
            raise JoinRequestDecisionForbidden
        lock_membership_scope(
            user_id=candidate.user_id,
            turnus_id=candidate.turnus_id,
        )
        join_request = TurnusJoinRequest.objects.select_for_update().select_related(
            "turnus", "user"
        ).get(pk=join_request_id)
        if join_request.status != TurnusJoinRequest.Status.PENDING:
            raise JoinRequestAlreadyResolved

        membership = None
        if decision == "approve":
            membership = TurnusMembership.objects.filter(
                user_id=join_request.user_id,
                turnus_id=join_request.turnus_id,
            ).first()
            if membership is None:
                membership = create_membership(
                    user=join_request.user,
                    turnus=join_request.turnus,
                    functional_role=TurnusMembership.FunctionalRole.TEAMER,
                )
            join_request.status = TurnusJoinRequest.Status.APPROVED
        else:
            join_request.status = TurnusJoinRequest.Status.REJECTED
        join_request.save(update_fields=("status", "updated_at"))

        request_id = (
            http_request.headers.get("X-Request-ID")
            if http_request is not None
            else None
        ) or f"join-request-{decision}-{join_request.pk}"
        record_audit_event(AuditEventData(
            turnus=join_request.turnus,
            actor_id=actor.pk,
            actor_label=actor_label_for_user(actor),
            action=f"join_request.{decision}",
            outcome="success",
            resource_type="turnus_join_request",
            resource_id=str(join_request.pk),
            resource_label=f"Beitrittsanfrage {join_request.pk}",
            request_id=request_id,
            client_ip=client_ip_from_request(http_request) if http_request is not None else "",
            user_agent=http_request.META.get("HTTP_USER_AGENT", "") if http_request is not None else "",
            details={
                "requester_id": join_request.user_id,
                "membership_id": membership.pk if membership is not None else None,
            },
        ))
        return join_request, membership


def _is_pending_constraint(error):
    cause = getattr(error, "__cause__", None)
    diag = getattr(cause, "diag", None)
    if getattr(diag, "constraint_name", None) == PENDING_CONSTRAINT:
        return True
    # SQLite does not report constraint names. Match the exact columns emitted for
    # this partial unique index; never infer a duplicate merely from an existing row.
    message = str(error)
    return (
        "UNIQUE constraint failed:" in message
        and "budo_app_turnusjoinrequest.user_id" in message
        and "budo_app_turnusjoinrequest.turnus_id" in message
    )


def _claim_notification(notification_id, *, now=None):
    now = now or timezone.now()
    stale_before = now - CLAIM_LEASE
    claimed = (
        TurnusJoinRequestNotification.objects.filter(pk=notification_id)
        .filter(
            Q(state=TurnusJoinRequestNotification.State.PENDING)
            | Q(
                state=TurnusJoinRequestNotification.State.SENDING,
                claimed_at__lt=stale_before,
            )
        )
        .update(
            state=TurnusJoinRequestNotification.State.SENDING,
            claimed_at=now,
            attempts=F("attempts") + 1,
            last_error="",
        )
        == 1
    )
    return now if claimed else None


def _delivery_headers(notification):
    domain = getattr(settings, "EMAIL_MESSAGE_ID_DOMAIN", "budobase.local")
    key = f"turnus-join-request-notification-{notification.pk}"
    return {
        "Message-ID": f"<{key}@{domain}>",
        # Providers which implement idempotency headers can use this stable key.
        "X-Idempotency-Key": key,
    }


def _deliver_notification(notification_id):
    """Claim and attempt one recipient delivery using durable at-least-once semantics.

    The claim is committed before SMTP so workers cannot concurrently send the same
    row, and each acknowledgement is conditional on the exact lease timestamp so an
    expired worker cannot mutate its successor's claim. A crash after SMTP accepts
    the message but before the delivered update can cause a retry; generic SMTP
    offers no atomic acknowledgement, so Message-ID and X-Idempotency-Key are
    deterministic to permit provider-side deduplication.
    """
    claim_token = _claim_notification(notification_id)
    if claim_token is None:
        return False

    notification = (
        TurnusJoinRequestNotification.objects.select_related(
            "join_request__user", "join_request__turnus"
        ).get(pk=notification_id)
    )
    join_request = notification.join_request
    requester = join_request.user
    body = (
        f"{requester.get_full_name() or requester.username} "
        f"<{requester.email}> bittet um Mitgliedschaft in {join_request.turnus}.\n\n"
        f"{IDENTITY_VERIFICATION_WARNING}"
    )
    try:
        delivered_count = EmailMessage(
            subject=f"Neue Beitrittsanfrage für {join_request.turnus}",
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[notification.recipient_email],
            headers=_delivery_headers(notification),
        ).send()
        if delivered_count != 1:
            raise RuntimeError(f"Email backend reported {delivered_count} deliveries")
    except Exception as exc:  # The backend boundary is intentionally failure-aware.
        TurnusJoinRequestNotification.objects.filter(
            pk=notification_id,
            state=TurnusJoinRequestNotification.State.SENDING,
            claimed_at=claim_token,
        ).update(
            state=TurnusJoinRequestNotification.State.PENDING,
            claimed_at=None,
            last_error=str(exc)[:2000],
        )
        logger.exception(
            "Join-request notification delivery failed",
            extra={"notification_id": notification.id},
        )
        return True

    TurnusJoinRequestNotification.objects.filter(
        pk=notification_id,
        state=TurnusJoinRequestNotification.State.SENDING,
        claimed_at=claim_token,
    ).update(
        state=TurnusJoinRequestNotification.State.DELIVERED,
        claimed_at=None,
        delivered_at=timezone.now(),
        last_error="",
    )
    return True


def deliver_pending_join_request_notifications(notification_ids=None):
    candidates = TurnusJoinRequestNotification.objects.filter(
        Q(state=TurnusJoinRequestNotification.State.PENDING)
        | Q(
            state=TurnusJoinRequestNotification.State.SENDING,
            claimed_at__lt=timezone.now() - CLAIM_LEASE,
        )
    )
    if notification_ids is not None:
        candidates = candidates.filter(pk__in=notification_ids)
    ids = list(candidates.order_by("id").values_list("id", flat=True))
    attempted = sum(bool(_deliver_notification(notification_id)) for notification_id in ids)
    return attempted


def _notification_for_leader(request, membership):
    email = (membership.user.email or "").strip()
    notification = TurnusJoinRequestNotification(
        join_request=request,
        recipient_user=membership.user,
        recipient_email=email,
    )
    try:
        validate_email(email)
    except ValidationError:
        notification.state = TurnusJoinRequestNotification.State.FAILED
        notification.last_error = "Leitung has no valid email address"
    return notification


def create_join_request(*, user, turnus):
    """Persist the request and one durable outbox row for every current Leitung."""
    try:
        with transaction.atomic():
            lock_membership_scope(user_id=user.pk, turnus_id=turnus.pk)
            if TurnusMembership.objects.filter(user=user, turnus=turnus).exists():
                raise AlreadyTurnusMember
            existing = TurnusJoinRequest.objects.filter(
                user=user, turnus=turnus, status=TurnusJoinRequest.Status.PENDING
            ).first()
            if existing:
                return existing, False

            request = TurnusJoinRequest.objects.create(user=user, turnus=turnus)
            leaders = list(
                TurnusMembership.objects.filter(
                    turnus=turnus,
                    functional_role=TurnusMembership.FunctionalRole.LEITUNG,
                ).select_related("user")
            )
            notifications = TurnusJoinRequestNotification.objects.bulk_create(
                [_notification_for_leader(request, membership) for membership in leaders]
            )
            notification_ids = [
                item.id
                for item in notifications
                if item.state == TurnusJoinRequestNotification.State.PENDING
            ]
            transaction.on_commit(
                lambda ids=notification_ids: deliver_pending_join_request_notifications(ids),
                robust=True,
            )
            return request, True
    except IntegrityError as error:
        if not _is_pending_constraint(error):
            raise
        return (
            TurnusJoinRequest.objects.get(
                user=user, turnus=turnus, status=TurnusJoinRequest.Status.PENDING
            ),
            False,
        )
