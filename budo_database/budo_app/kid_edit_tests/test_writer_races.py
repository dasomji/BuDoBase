from budo_app.test_membership_fixtures import approve_and_select_turnus
import json
import sys
from contextlib import ExitStack, contextmanager
from datetime import date
from io import StringIO
from queue import Queue
from threading import Barrier, Event, Thread, current_thread
from time import monotonic
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.db import close_old_connections, connection, connections, transaction
from django.test import Client, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse

from budo_app import kids_views, schwerpunkte_views, views
from budo_app.happy_cleaning_assignment_commands import (
    assign_child,
    set_child_number,
)
from budo_app.happy_cleaning_commands import CommandContext
from budo_app.kid_edit_writes import versioned_child_write
from budo_app.management.commands import fix_html_entities
from budo_app.models import (
    HappyCleaning,
    HappyCleaningAssignment,
    HappyCleaningStation,
    Kinder,
    Schwerpunkte,
    SchwerpunktWahl,
    Schwerpunktzeit,
    Turnus,
)


@skipUnlessDBFeature("has_select_for_update")
class VersionedWriterPostgreSQLRaceTests(TransactionTestCase):
    reset_sequences = True
    join_timeout = 20

    def setUp(self):
        if connection.vendor != "postgresql":
            self.skipTest("Independent row-lock races require PostgreSQL.")
        cache.clear()
        self.turnus = Turnus.objects.create(
            turnus_nr=16107,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(username="writer-race-actor")
        approve_and_select_turnus(self.user, self.turnus)
        self.user.profil.rufname = "Synthetic Actor"
        self.user.profil.save()
        self.period_w1 = Schwerpunktzeit.objects.get(
            turnus=self.turnus,
            woche="w1",
        )
        self.period_w2 = Schwerpunktzeit.objects.get(
            turnus=self.turnus,
            woche="w2",
        )
        self.focus_w1 = Schwerpunkte.objects.create(
            swp_name="Synthetic week one",
            schwerpunktzeit=self.period_w1,
        )
        self.focus_w2 = Schwerpunkte.objects.create(
            swp_name="Synthetic week two",
            schwerpunktzeit=self.period_w2,
        )
        self.focus_w2_alternative = Schwerpunkte.objects.create(
            swp_name="Synthetic week two alternative",
            schwerpunktzeit=self.period_w2,
        )
        self.child = Kinder.objects.create(
            kid_index="SYNTHETIC-RACE-161-07",
            kid_vorname="Initial",
            kid_nachname="Child",
            kid_birthday=date(2011, 1, 1),
            turnus=self.turnus,
            illness="Initial condition",
            sozialversicherungsnr="1234 020712",
            einverstaendnis_erklaerung=False,
        )
        self.child.schwerpunkte.add(self.focus_w2)
        SchwerpunktWahl.objects.create(
            kind=self.child,
            schwerpunktzeit=self.period_w2,
            erste_wahl=self.focus_w2,
        )

    def new_client(self):
        client = Client()
        client.force_login(User.objects.get(pk=self.user.pk))
        return client

    def race(self, *operations):
        barrier = Barrier(len(operations))
        results = Queue()

        def run(index, operation):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                results.put((index, "ok", operation()))
            except Exception as error:
                results.put((index, "error", type(error).__name__))
            finally:
                connections.close_all()

        threads = [
            Thread(
                target=run,
                args=(index, operation),
                daemon=True,
                name=f"synthetic-writer-race-{index}",
            )
            for index, operation in enumerate(operations)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=self.join_timeout)
        connections.close_all()

        alive = [thread.name for thread in threads if thread.is_alive()]
        self.assertEqual(alive, [], "Writer race exceeded the deadlock watchdog.")
        outcomes = [results.get(timeout=1) for _thread in threads]
        outcomes.sort()
        failures = [
            error_type
            for _index, status, error_type in outcomes
            if status == "error"
        ]
        self.assertEqual(
            failures,
            [],
            "Worker failed; sanitized exception types: "
            + ", ".join(failures),
        )
        return [value for _index, _status, value in outcomes]

    @contextmanager
    def scheduled_real_boundary(self, *writer_modules):
        first_acquired = Event()
        competitor_attempted = Event()
        competitor_blocked = Event()
        first_resumed = Event()
        competitor_acquired = Event()
        competitor_backend_pids = Queue()
        polling_pause = Event()
        real_boundary = versioned_child_write

        @contextmanager
        def scheduled_boundary(*, turnus_id, child_id):
            is_first_writer = current_thread().name.endswith("-0")
            if is_first_writer:
                with real_boundary(
                    turnus_id=turnus_id,
                    child_id=child_id,
                ) as write:
                    first_acquired.set()
                    if not competitor_attempted.wait(timeout=10):
                        raise RuntimeError(
                            "synthetic competitor-attempt watchdog"
                        )
                    competitor_pid = competitor_backend_pids.get(timeout=1)
                    lock_wait_deadline = monotonic() + 10
                    while monotonic() < lock_wait_deadline:
                        with connection.cursor() as cursor:
                            cursor.execute(
                                """
                                SELECT wait_event_type
                                FROM pg_stat_activity
                                WHERE pid = %s
                                """,
                                (competitor_pid,),
                            )
                            activity = cursor.fetchone()
                        if activity == ("Lock",):
                            competitor_blocked.set()
                            break
                        polling_pause.wait(timeout=0.01)
                    if not competitor_blocked.is_set():
                        raise RuntimeError(
                            "synthetic competitor-lock watchdog"
                        )
                    first_resumed.set()
                    yield write
                return

            if not first_acquired.wait(timeout=10):
                raise RuntimeError("synthetic first-acquisition watchdog")
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                competitor_backend_pids.put(cursor.fetchone()[0])
            competitor_attempted.set()
            with real_boundary(
                turnus_id=turnus_id,
                child_id=child_id,
            ) as write:
                if not first_resumed.is_set():
                    raise RuntimeError("synthetic boundary-order failure")
                competitor_acquired.set()
                yield write

        with ExitStack() as patches:
            for writer_module in writer_modules:
                patches.enter_context(
                    patch.object(
                        writer_module,
                        "versioned_child_write",
                        new=scheduled_boundary,
                    )
                )
            yield

        self.assertTrue(first_acquired.is_set())
        self.assertTrue(competitor_attempted.is_set())
        self.assertTrue(competitor_blocked.is_set())
        self.assertTrue(first_resumed.is_set())
        self.assertTrue(competitor_acquired.is_set())

    def post_swp(self, *, focus_id, choice_rank="1"):
        return self.new_client().post(
            reverse("update_schwerpunkt_wahl"),
            data=json.dumps(
                {
                    "kid_id": self.child.pk,
                    "swp_id": focus_id,
                    "choice_rank": choice_rank,
                }
            ),
            content_type="application/json",
        )

    def post_check_in(self):
        return self.new_client().post(
            reverse("check_in", args=(self.child.pk,)),
            {
                "check_in_date": "2026-07-01",
                "einverstaendnis_erklaerung": "on",
                "notiz": "",
                "amount": "",
            },
        )

    def scalar_write(self, *, field_name, value):
        with versioned_child_write(
            turnus_id=self.turnus.pk,
            child_id=self.child.pk,
        ) as write:
            setattr(write.child, field_name, value)
            write.save_child(update_fields=(field_name,))

    def test_swp_endpoint_and_ordinary_covered_writer_serialize(self):
        with self.scheduled_real_boundary(
            schwerpunkte_views,
            sys.modules[__name__],
        ):
            responses = self.race(
                lambda: self.post_swp(focus_id=self.focus_w2_alternative.pk),
                lambda: self.scalar_write(
                    field_name="illness",
                    value="Updated condition",
                ),
            )

        self.assertEqual(responses[0].status_code, 200)
        self.assertEqual(responses[0].json(), {"status": "success"})
        self.child.refresh_from_db()
        self.assertEqual(self.child.illness, "Updated condition")
        self.assertEqual(self.child.edit_version, 3)
        self.assertEqual(
            set(self.child.schwerpunkte.values_list("pk", flat=True)),
            {self.focus_w2_alternative.pk},
        )

    def test_consent_and_birthday_writers_preserve_both_changes(self):
        with self.scheduled_real_boundary(kids_views, views):
            responses = self.race(
                self.post_check_in,
                lambda: self.new_client().post(
                    reverse("update_birthdays_from_sv")
                ),
            )

        self.assertEqual(
            sorted(response.status_code for response in responses),
            [302, 302],
        )
        self.child.refresh_from_db()
        self.assertIs(self.child.einverstaendnis_erklaerung, True)
        self.assertEqual(self.child.kid_birthday, date(2012, 7, 2))
        self.assertEqual(self.child.edit_version, 3)

    def test_identical_canonical_writes_have_at_most_one_effective_bump(self):
        with self.scheduled_real_boundary(sys.modules[__name__]):
            self.race(
                lambda: self.scalar_write(
                    field_name="illness",
                    value="Canonical target",
                ),
                lambda: self.scalar_write(
                    field_name="illness",
                    value="Canonical target",
                ),
            )

        self.child.refresh_from_db()
        self.assertEqual(self.child.illness, "Canonical target")
        self.assertEqual(self.child.edit_version, 2)

    def test_distinct_covered_writes_are_preserved_with_monotonic_version(self):
        with self.scheduled_real_boundary(sys.modules[__name__]):
            self.race(
                lambda: self.scalar_write(
                    field_name="kid_vorname",
                    value="Updated",
                ),
                lambda: self.scalar_write(
                    field_name="illness",
                    value="Distinct condition",
                ),
            )

        self.child.refresh_from_db()
        self.assertEqual(self.child.kid_vorname, "Updated")
        self.assertEqual(self.child.illness, "Distinct condition")
        self.assertEqual(self.child.edit_version, 3)

    def test_cleanup_and_interactive_writer_serialize_without_lost_update(self):
        Kinder.objects.filter(pk=self.child.pk).update(
            illness="Synthetic &lt;condition&gt;",
        )

        with self.scheduled_real_boundary(fix_html_entities, kids_views):
            responses = self.race(
                lambda: call_command(
                    "fix_html_entities",
                    turnus_id=self.turnus.pk,
                    stdout=StringIO(),
                ),
                self.post_check_in,
            )

        self.assertIsNone(responses[0])
        self.assertEqual(responses[1].status_code, 302)
        self.child.refresh_from_db()
        self.assertEqual(self.child.illness, "Synthetic <condition>")
        self.assertIs(self.child.einverstaendnis_erklaerung, True)
        self.assertEqual(self.child.edit_version, 3)

    def test_focus_move_after_resolution_rejects_stale_rank_only_choice(self):
        original_second_choice = SchwerpunktWahl.objects.get(
            kind=self.child,
            schwerpunktzeit=self.period_w2,
        ).zweite_wahl_id
        endpoint_at_protocol = Event()
        focus_move_committed = Event()
        real_versioned_child_write = schwerpunkte_views.versioned_child_write

        def paused_versioned_child_write(*, turnus_id, child_id):
            endpoint_at_protocol.set()
            if not focus_move_committed.wait(timeout=10):
                raise RuntimeError("synthetic focus-move watchdog")
            return real_versioned_child_write(
                turnus_id=turnus_id,
                child_id=child_id,
            )

        def move_focus():
            if not endpoint_at_protocol.wait(timeout=10):
                raise RuntimeError("synthetic endpoint-resolution watchdog")
            with transaction.atomic():
                updated = Schwerpunkte.objects.filter(
                    pk=self.focus_w2_alternative.pk,
                ).update(schwerpunktzeit=self.period_w1)
                if updated != 1:
                    raise RuntimeError("synthetic focus move failed")
            focus_move_committed.set()

        with patch.object(
            schwerpunkte_views,
            "versioned_child_write",
            side_effect=paused_versioned_child_write,
        ):
            responses = self.race(
                lambda: self.post_swp(
                    focus_id=self.focus_w2_alternative.pk,
                    choice_rank="2",
                ),
                move_focus,
            )

        response = responses[0]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")
        self.child.refresh_from_db()
        self.assertEqual(self.child.edit_version, 1)
        self.assertEqual(
            SchwerpunktWahl.objects.get(
                kind=self.child,
                schwerpunktzeit=self.period_w2,
            ).zweite_wahl_id,
            original_second_choice,
        )
        self.focus_w2_alternative.refresh_from_db()
        self.assertEqual(
            self.focus_w2_alternative.schwerpunktzeit_id,
            self.period_w1.pk,
        )

    def test_happy_cleaning_commands_keep_edit_version_independent(self):
        event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
            revision=1,
        )
        station = HappyCleaningStation.objects.create(
            happy_cleaning=event,
            name="Synthetic station",
            max_kids=2,
            meeting_point="Synthetic meeting point",
            position=1,
        )
        context = CommandContext(
            turnus=self.turnus,
            actor_id=self.user.pk,
            actor_label="Synthetic Actor",
            request_id="synthetic-number-161-07",
            client_ip=None,
            user_agent="synthetic-race-test",
        )

        number_result, number_replayed = set_child_number(
            context,
            self.child.pk,
            7,
            1,
        )
        assignment_context = CommandContext(
            turnus=self.turnus,
            actor_id=self.user.pk,
            actor_label="Synthetic Actor",
            request_id="synthetic-assignment-161-07",
            client_ip=None,
            user_agent="synthetic-race-test",
        )
        assignment_result, assignment_replayed = assign_child(
            assignment_context,
            event.pk,
            self.child.pk,
            station.pk,
        )

        self.child.refresh_from_db()
        event.refresh_from_db()
        assignment = HappyCleaningAssignment.objects.get(
            happy_cleaning=event,
            child=self.child,
        )
        self.assertFalse(number_replayed)
        self.assertFalse(assignment_replayed)
        self.assertEqual(number_result["child"]["number_version"], 2)
        self.assertEqual(self.child.happy_cleaning_number_version, 2)
        self.assertGreater(event.revision, 1)
        self.assertEqual(assignment.version, assignment_result["assignment"]["version"])
        self.assertEqual(self.child.edit_version, 1)
