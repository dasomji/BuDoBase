import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import (
    TurnusJoinRequest,
    TurnusJoinRequestNotification,
    TurnusMembership,
)


logger = logging.getLogger(__name__)

IDENTITY_VERIFICATION_WARNING = (
    "Bitte kontaktiere die Person über einen dir bekannten, unabhängigen Kanal. "
    "Prüfe dabei, dass die E-Mail-Adresse wirklich zu ihr gehört und dass sie "
    "diese Anfrage selbst gestellt hat."
)


class AlreadyTurnusMember(Exception):
    pass


def _deliver_notification(notification_id):
    """Attempt one durable delivery; known failures remain available for retry."""
    with transaction.atomic():
        notification = (
            TurnusJoinRequestNotification.objects.select_for_update()
            .select_related("join_request__user", "join_request__turnus")
            .get(pk=notification_id)
        )
        if notification.delivered_at is not None:
            return True

        join_request = notification.join_request
        requester = join_request.user
        body = (
            f"{requester.get_full_name() or requester.username} "
            f"<{requester.email}> bittet um Mitgliedschaft in {join_request.turnus}.\n\n"
            f"{IDENTITY_VERIFICATION_WARNING}"
        )
        notification.attempts += 1
        try:
            delivered_count = send_mail(
                f"Neue Beitrittsanfrage für {join_request.turnus}",
                body,
                settings.DEFAULT_FROM_EMAIL,
                [notification.recipient_email],
            )
            if delivered_count != 1:
                raise RuntimeError(
                    f"Email backend reported {delivered_count} deliveries"
                )
        except Exception as exc:  # The backend boundary is intentionally failure-aware.
            notification.last_error = str(exc)[:2000]
            notification.save(update_fields=("attempts", "last_error"))
            logger.exception(
                "Join-request notification delivery failed",
                extra={"notification_id": notification.id},
            )
            return False

        notification.delivered_at = timezone.now()
        notification.last_error = ""
        notification.save(
            update_fields=("attempts", "last_error", "delivered_at")
        )
        return True


def deliver_pending_join_request_notifications(notification_ids=None):
    queryset = TurnusJoinRequestNotification.objects.filter(delivered_at__isnull=True)
    if notification_ids is not None:
        queryset = queryset.filter(pk__in=notification_ids)
    ids = list(queryset.order_by("id").values_list("id", flat=True))
    for notification_id in ids:
        _deliver_notification(notification_id)
    return len(ids)


def create_join_request(*, user, turnus):
    """Persist the request and its recipient outbox without granting access."""
    if TurnusMembership.objects.filter(user=user, turnus=turnus).exists():
        raise AlreadyTurnusMember

    try:
        with transaction.atomic():
            request = TurnusJoinRequest.objects.create(user=user, turnus=turnus)
            leaders = list(
                TurnusMembership.objects.filter(
                    turnus=turnus,
                    functional_role=TurnusMembership.FunctionalRole.LEITUNG,
                )
                .exclude(user__email="")
                .select_related("user")
            )
            notifications = TurnusJoinRequestNotification.objects.bulk_create(
                [
                    TurnusJoinRequestNotification(
                        join_request=request,
                        recipient_user=membership.user,
                        recipient_email=membership.user.email,
                    )
                    for membership in leaders
                ]
            )
            notification_ids = [notification.id for notification in notifications]
            transaction.on_commit(
                lambda ids=notification_ids: deliver_pending_join_request_notifications(ids),
                robust=True,
            )
            return request, True
    except IntegrityError as integrity_error:
        try:
            return (
                TurnusJoinRequest.objects.get(
                    user=user,
                    turnus=turnus,
                    status=TurnusJoinRequest.Status.PENDING,
                ),
                False,
            )
        except TurnusJoinRequest.DoesNotExist:
            raise integrity_error
