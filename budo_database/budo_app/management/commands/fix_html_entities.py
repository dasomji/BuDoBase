"""
Django management command to fix HTML entities in existing Kinder records.
This command will decode HTML entities like &#039; to their proper characters.
"""

import html
from django.core.management.base import BaseCommand
from django.db import transaction

from budo_app.kid_edit_writes import (
    COVERED_KINDER_FIELDS,
    versioned_child_write,
)
from budo_app.models import Kinder


class Command(BaseCommand):
    help = 'Fix HTML entities in existing Kinder records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually making changes',
        )
        parser.add_argument(
            '--turnus-id',
            type=int,
            help='Only fix records for a specific turnus ID',
        )

    def decode_html_entities(self, text):
        """
        Decode HTML entities in text fields.
        Returns the original text if it's None or empty.
        """
        if not text:
            return text
        text_str = str(text)
        if text_str.lower().strip() in ("nan", "none", ""):
            return text
        decoded = html.unescape(text_str)
        return decoded if decoded != text_str else text

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        turnus_id = options.get('turnus_id')

        # Define the fields that might contain HTML entities
        text_fields = [
            'kid_vorname', 'kid_nachname', 'geschwister', 'zeltwunsch',
            'schimmkenntnisse', 'haftpflichtversicherung', 'anmerkung',
            'anmerkung_buchung', 'anmelder_vorname', 'anmelder_nachname',
            'anmelde_organisation', 'anmelder_email', 'anmelder_mobil',
            'hauptversichert_bei', 'notfall_kontakte', 'rechnungsadresse',
            'rechnung_ort', 'rechnung_land', 'sex', 'sozialversicherungsnr',
            'tetanusimpfung', 'zeckenimpfung', 'vegetarisch',
            'special_food_description', 'drugs', 'illness',
            'rezeptfreie_medikamente', 'rezept_medikamente', 'swimmer'
        ]

        # Get queryset
        queryset = Kinder.objects.all()
        if turnus_id:
            queryset = queryset.filter(turnus_id=turnus_id)
        queryset = queryset.order_by("pk")

        self.stdout.write(f"Processing {queryset.count()} Kinder records...")

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "DRY RUN MODE - No changes will be made"))

        updated_count = 0
        changes_made = []

        with transaction.atomic():
            for kid in queryset:
                kid_changes = {}

                for field_name in text_fields:
                    original_value = getattr(kid, field_name)
                    if original_value:
                        decoded_value = self.decode_html_entities(
                            original_value)
                        if decoded_value != original_value:
                            kid_changes[field_name] = decoded_value

                if kid_changes:
                    changes_made.append({
                        'kid_id': kid.pk,
                        'fields': tuple(kid_changes),
                    })

                    if not dry_run:
                        changed_fields = tuple(kid_changes)
                        has_covered_change = any(
                            field_name in COVERED_KINDER_FIELDS
                            for field_name in changed_fields
                        )
                        if has_covered_change:
                            with versioned_child_write(
                                turnus_id=kid.turnus_id,
                                child_id=kid.pk,
                            ) as write:
                                for (
                                    field_name,
                                    decoded_value,
                                ) in kid_changes.items():
                                    setattr(write.child, field_name, decoded_value)
                                write.save_child(update_fields=changed_fields)
                        else:
                            for field_name, decoded_value in kid_changes.items():
                                setattr(kid, field_name, decoded_value)
                            kid.save(update_fields=changed_fields)

                    updated_count += 1

        # Report results
        if dry_run:
            self.stdout.write(f"\nWould update {updated_count} records:")
        else:
            self.stdout.write(f"\nUpdated {updated_count} records:")

        for item in changes_made:
            self.stdout.write(f"\n  Kid ID: {item['kid_id']}")
            self.stdout.write(f"    Fields: {', '.join(item['fields'])}")

        if not dry_run and updated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSuccessfully fixed HTML entities in {updated_count} records!")
            )
        elif updated_count == 0:
            self.stdout.write(
                self.style.SUCCESS("No HTML entities found that need fixing.")
            )
