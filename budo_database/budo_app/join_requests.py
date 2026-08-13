from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction

from .models import TurnusJoinRequest, TurnusMembership


IDENTITY_VERIFICATION_WARNING = (
    "Bitte kontaktiere die Person über einen dir bekannten, unabhängigen Kanal. "
    "Prüfe dabei, dass die E-Mail-Adresse wirklich zu ihr gehört und dass sie "
    "diese Anfrage selbst gestellt hat."
)


def _notify_leitung(join_request_id):
    join_request = TurnusJoinRequest.objects.select_related("user", "turnus").get(
        pk=join_request_id
    )
    recipients = (
        TurnusMembership.objects.filter(
            turnus=join_request.turnus,
            functional_role=TurnusMembership.FunctionalRole.LEITUNG,
        )
        .exclude(user__email="")
        .values_list("user__email", flat=True)
    )
    requester = join_request.user
    body = (
        f"{requester.get_full_name() or requester.username} "
        f"<{requester.email}> bittet um Mitgliedschaft in {join_request.turnus}.\n\n"
        f"{IDENTITY_VERIFICATION_WARNING}"
    )
    for recipient in recipients:
        send_mail(
            f"Neue Beitrittsanfrage für {join_request.turnus}",
            body,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
        )


def create_join_request(*, user, turnus):
    """Create a request without granting access and notify once after commit."""
    try:
        with transaction.atomic():
            request = TurnusJoinRequest.objects.create(user=user, turnus=turnus)
            transaction.on_commit(lambda request_id=request.pk: _notify_leitung(request_id))
            return request, True
    except IntegrityError:
        return (
            TurnusJoinRequest.objects.get(
                user=user, turnus=turnus, status=TurnusJoinRequest.Status.PENDING
            ),
            False,
        )
