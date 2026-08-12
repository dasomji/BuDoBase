from django.core.management.base import BaseCommand
from django.db.models import Q

from budo_app.location_services import update_auslagerorte_travel_times
from budo_app.models import Auslagerorte


class Command(BaseCommand):
    help = "Backfill missing travel times from BuDo for Auslagerorte."

    def handle(self, *args, **options):
        candidates = (
            Auslagerorte.objects.exclude(koordinaten__isnull=True)
            .exclude(koordinaten="")
            .filter(Q(driving_minutes__isnull=True) | Q(walking_minutes__isnull=True))
            .order_by("id")
        )

        updated = 0
        for place in candidates.iterator():
            update_auslagerorte_travel_times(place)
            place.save(update_fields=["driving_minutes", "walking_minutes"])
            updated += 1
            self.stdout.write(f"{place.name}: Reisezeiten aktualisiert")

        self.stdout.write(self.style.SUCCESS(f"{updated} Auslagerorte verarbeitet."))
