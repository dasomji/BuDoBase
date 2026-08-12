from django.core.management.base import BaseCommand
from django.db.models import Q

from budo_app.location_services import update_auslagerorte_coordinates
from budo_app.models import Auslagerorte


class Command(BaseCommand):
    help = (
        "Backfill missing Auslagerort and Parkspot coordinates from "
        "Google Maps links."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--enrich-addresses",
            action="store_true",
            help="Fill empty address fields when main-location coordinates are found.",
        )

    def handle(self, *args, **options):
        candidates = Auslagerorte.objects.filter(
            Q(maps_link__gt="", koordinaten__isnull=True)
            | Q(maps_link__gt="", koordinaten="")
            | Q(maps_link_parkspot__gt="", koordinaten_parkspot__isnull=True)
            | Q(maps_link_parkspot__gt="", koordinaten_parkspot="")
        ).order_by("id")

        updated = 0
        failed = 0
        for place in candidates.iterator():
            main_missing = bool(place.maps_link) and not place.koordinaten
            parking_missing = (
                bool(place.maps_link_parkspot)
                and not place.koordinaten_parkspot
            )
            place._maps_link_changed = main_missing
            place._maps_link_parkspot_changed = parking_missing
            place._enrich_address = options["enrich_addresses"]
            update_auslagerorte_coordinates(place)

            place.save()
            warnings = getattr(place, "_location_warnings", [])
            main_updated = main_missing and bool(place.koordinaten)
            parking_updated = parking_missing and bool(place.koordinaten_parkspot)
            if main_updated or parking_updated:
                updated += 1
                self.stdout.write(f"{place.name}: Koordinaten aktualisiert")
            if warnings:
                failed += 1
                for warning in warnings:
                    self.stderr.write(self.style.WARNING(f"{place.name}: {warning}"))

        self.stdout.write(self.style.SUCCESS(
            f"{updated} Auslagerorte aktualisiert; {failed} mit Warnungen."
        ))
