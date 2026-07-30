from contextlib import contextmanager
from datetime import date
from io import StringIO
from unittest.mock import patch

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase

from budo_app.models import Kinder, Turnus


class FixHtmlEntitiesCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.turnus = Turnus.objects.create(
            turnus_nr=16106,
            turnus_beginn=date(2026, 7, 1),
        )
        cls.other_turnus = Turnus.objects.create(
            turnus_nr=16107,
            turnus_beginn=date(2026, 8, 1),
        )

    def create_kid(self, *, turnus=None, index="SYNTHETIC-161-06", **fields):
        values = {
            "kid_index": index,
            "kid_vorname": "Synthetic",
            "kid_nachname": "Child",
            "kid_birthday": date(2012, 7, 2),
            "turnus": turnus or self.turnus,
            "anmelder_vorname": "Synthetic",
            "anmelder_nachname": "Guardian",
            "rechnungsadresse": "Synthetic street 1",
            "rechnung_ort": "Vienna",
            "rechnung_land": "Austria",
        }
        values.update(fields)
        return Kinder.objects.create(**values)

    def run_command(self, **options):
        output = StringIO()
        call_command("fix_html_entities", stdout=output, **options)
        return output.getvalue()

    def test_multiple_covered_field_changes_bump_child_once(self):
        child = self.create_kid(
            kid_vorname="Synthetic &amp; First",
            kid_nachname="Synthetic &quot;Last&quot;",
            illness="Synthetic &lt;condition&gt;",
        )

        output = self.run_command()

        child.refresh_from_db()
        self.assertEqual(
            (
                child.kid_vorname,
                child.kid_nachname,
                child.illness,
                child.edit_version,
            ),
            (
                "Synthetic & First",
                'Synthetic "Last"',
                "Synthetic <condition>",
                2,
            ),
        )
        self.assertIn("Successfully fixed HTML entities in 1 records", output)

    def test_uncovered_only_cleanup_persists_without_bump(self):
        child = self.create_kid(
            anmerkung="Synthetic &amp; uncovered",
        )

        self.run_command()

        child.refresh_from_db()
        self.assertEqual(child.anmerkung, "Synthetic & uncovered")
        self.assertEqual(child.edit_version, 1)

    def test_uncovered_only_cleanup_invalidates_turnus_cache(self):
        child = self.create_kid(
            anmerkung="Synthetic &amp; uncovered",
        )
        cache_key = f"turnus_data_{self.turnus.pk}"
        cache.set(cache_key, {"synthetic": "stale"}, 60)

        self.run_command()

        child.refresh_from_db()
        self.assertEqual(child.anmerkung, "Synthetic & uncovered")
        self.assertIsNone(cache.get(cache_key))
        self.assertEqual(child.edit_version, 1)

    def test_no_entity_does_not_bump(self):
        child = self.create_kid()

        output = self.run_command()

        child.refresh_from_db()
        self.assertEqual(child.edit_version, 1)
        self.assertIn("No HTML entities found that need fixing.", output)

    def test_dry_run_changes_nothing_and_does_not_bump(self):
        child = self.create_kid(
            kid_vorname="Synthetic &amp; dry run",
            illness="Synthetic &lt;dry&gt;",
        )

        output = self.run_command(dry_run=True)

        child.refresh_from_db()
        self.assertEqual(
            (
                child.kid_vorname,
                child.illness,
                child.edit_version,
            ),
            (
                "Synthetic &amp; dry run",
                "Synthetic &lt;dry&gt;",
                1,
            ),
        )
        self.assertIn("DRY RUN MODE - No changes will be made", output)

    def test_turnus_filter_isolates_other_turnus_rows(self):
        selected = self.create_kid(
            index="SYNTHETIC-SELECTED-161-06",
            illness="Synthetic &lt;selected&gt;",
        )
        foreign = self.create_kid(
            turnus=self.other_turnus,
            index="SYNTHETIC-FOREIGN-161-06",
            illness="Synthetic &lt;foreign&gt;",
        )

        self.run_command(turnus_id=self.turnus.pk)

        selected.refresh_from_db()
        foreign.refresh_from_db()
        self.assertEqual(
            (
                selected.illness,
                selected.edit_version,
                foreign.illness,
                foreign.edit_version,
            ),
            (
                "Synthetic <selected>",
                2,
                "Synthetic &lt;foreign&gt;",
                1,
            ),
        )

    def test_changed_children_enter_protocol_in_primary_key_order(self):
        first = self.create_kid(
            index="SYNTHETIC-ZULU-161-06",
            kid_vorname="Zulu &amp; first",
        )
        second = self.create_kid(
            index="SYNTHETIC-ALPHA-161-06",
            kid_vorname="Alpha &amp; second",
        )
        write_order = []
        from budo_app.kid_edit_writes import versioned_child_write

        @contextmanager
        def recording_versioned_child_write(*, turnus_id, child_id):
            write_order.append(child_id)
            with versioned_child_write(
                turnus_id=turnus_id,
                child_id=child_id,
            ) as write:
                yield write

        with patch(
            "budo_app.management.commands.fix_html_entities.versioned_child_write",
            new=recording_versioned_child_write,
            create=True,
        ):
            self.run_command()

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(
            (
                write_order,
                first.edit_version,
                second.edit_version,
            ),
            (
                [first.pk, second.pk],
                2,
                2,
            ),
        )

    def test_later_child_failure_rolls_back_all_cleanup_and_versions(self):
        first = self.create_kid(
            index="SYNTHETIC-FIRST-ROLLBACK-161-06",
            illness="Synthetic &lt;first&gt;",
        )
        second = self.create_kid(
            index="SYNTHETIC-SECOND-ROLLBACK-161-06",
            illness="Synthetic &lt;second&gt;",
        )
        original_save = Kinder.save

        def fail_second_version_save(instance, *args, **kwargs):
            if (
                instance.pk == second.pk
                and tuple(kwargs.get("update_fields") or ())
                == ("edit_version",)
            ):
                raise RuntimeError("synthetic cleanup persistence failure")
            return original_save(instance, *args, **kwargs)

        failure = None
        with patch.object(Kinder, "save", new=fail_second_version_save):
            try:
                self.run_command()
            except RuntimeError as error:
                failure = error

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(
            (
                str(failure),
                first.illness,
                first.edit_version,
                second.illness,
                second.edit_version,
            ),
            (
                "synthetic cleanup persistence failure",
                "Synthetic &lt;first&gt;",
                1,
                "Synthetic &lt;second&gt;",
                1,
            ),
        )

    def test_output_never_includes_names_or_before_after_values(self):
        child = self.create_kid(
            kid_vorname="SYNTHETIC_PRIVATE_NAME &amp;",
            illness="SYNTHETIC_PRIVATE_BEFORE &lt;value&gt;",
        )

        output = self.run_command()

        child.refresh_from_db()
        self.assertNotIn("SYNTHETIC_PRIVATE_NAME", output)
        self.assertNotIn("SYNTHETIC_PRIVATE_BEFORE", output)
        self.assertNotIn(" -> ", output)
        self.assertEqual(child.edit_version, 2)
