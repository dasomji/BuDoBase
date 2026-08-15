from django.core.management.base import BaseCommand

from budo_app.join_requests import deliver_pending_join_request_notifications
from budo_app.models import TurnusJoinRequestNotification


class Command(BaseCommand):
    help = "Retry undelivered Turnus join-request notification outbox entries."

    def handle(self, *args, **options):
        attempted = deliver_pending_join_request_notifications()
        self.stdout.write(f"Attempted {attempted} pending notification(s).")
        failures = TurnusJoinRequestNotification.objects.filter(
            state=TurnusJoinRequestNotification.State.FAILED
        ).select_related("recipient_user", "join_request__turnus")
        if failures:
            self.stderr.write(
                f"{failures.count()} notification(s) require operator action:"
            )
            for item in failures:
                self.stderr.write(
                    f"#{item.id} {item.recipient_user} / {item.join_request.turnus}: "
                    f"{item.last_error}"
                )
