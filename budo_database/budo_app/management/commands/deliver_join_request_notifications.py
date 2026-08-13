from django.core.management.base import BaseCommand

from budo_app.join_requests import deliver_pending_join_request_notifications


class Command(BaseCommand):
    help = "Retry undelivered Turnus join-request notification outbox entries."

    def handle(self, *args, **options):
        attempted = deliver_pending_join_request_notifications()
        self.stdout.write(f"Attempted {attempted} pending notification(s).")
