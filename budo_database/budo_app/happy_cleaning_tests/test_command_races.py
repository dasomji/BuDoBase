import json
from datetime import date
from queue import Empty, Queue
from threading import Barrier, Thread
from time import monotonic
from unittest import skipUnless

from django.contrib.auth.models import User
from django.db import close_old_connections, connection, connections
from django.test import Client, TransactionTestCase
from django.urls import reverse

from budo_app.happy_cleaning_tests.task_fixtures import CanonicalTask

from budo_app.models import (
    HappyCleaning,
    HappyCleaningStation,
    Turnus,
)


@skipUnless(
    connection.vendor == "postgresql",
    "Row-locking command races require PostgreSQL.",
)
class HappyCleaningManagementRaceTests(TransactionTestCase):
    reset_sequences = True
    worker_timeout = 20
    cleanup_grace = 12
    lock_timeout = "5000ms"
    statement_timeout = "10000ms"

    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.users = []
        for index in range(2):
            user = User.objects.create_user(username=f"race-editor-{index}")
            user.profil.turnus = self.turnus
            user.profil.save(update_fields=["turnus"])
            self.users.append(user)

    def concurrent_posts(self, url, payloads):
        barrier = Barrier(2)
        results = Queue()

        def post(index):
            response_value = None
            error_types = []
            try:
                close_old_connections()
                connection.ensure_connection()
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT set_config('lock_timeout', %s, false)",
                        (self.lock_timeout,),
                    )
                    cursor.execute(
                        "SELECT set_config('statement_timeout', %s, false)",
                        (self.statement_timeout,),
                    )
                client = Client()
                client.force_login(self.users[index])
                barrier.wait(timeout=10)
                response = client.post(
                    url[index] if isinstance(url, list) else url,
                    data=json.dumps(payloads[index]),
                    content_type="application/json",
                )
                response_value = response.status_code, response.json()
            except BaseException as error:
                error_types.append(type(error).__name__)
            finally:
                try:
                    connections.close_all()
                except BaseException as error:
                    error_types.append(type(error).__name__)
                results.put((index, response_value, tuple(error_types)))

        threads = [
            Thread(
                target=post,
                args=(index,),
                daemon=True,
                name=f"happy-cleaning-command-race-{index}",
            )
            for index in range(2)
        ]
        for thread in threads:
            thread.start()

        worker_deadline = monotonic() + self.worker_timeout
        for thread in threads:
            thread.join(timeout=max(0, worker_deadline - monotonic()))

        timed_out_indices = tuple(
            index
            for index, thread in enumerate(threads)
            if thread.is_alive()
        )
        if timed_out_indices:
            cleanup_deadline = monotonic() + self.cleanup_grace
            for thread in threads:
                thread.join(timeout=max(0, cleanup_deadline - monotonic()))

        outcomes = {}
        while True:
            try:
                index, response_value, error_types = results.get_nowait()
            except Empty:
                break
            outcomes[index] = (response_value, error_types)

        completed_error_types = tuple(
            error_type
            for _response_value, error_types in outcomes.values()
            for error_type in error_types
        )
        self._assert_worker_health(
            timed_out_indices=timed_out_indices,
            completed_indices=tuple(outcomes),
            completed_error_types=completed_error_types,
            expected_workers=len(threads),
        )
        return [
            outcomes[index][0]
            for index in range(len(threads))
        ]

    def _assert_worker_health(
            self,
            *,
            timed_out_indices,
            completed_indices,
            completed_error_types,
            expected_workers):
        incomplete_indices = tuple(
            index
            for index in range(expected_workers)
            if index not in completed_indices
        )
        if (
            timed_out_indices
            or incomplete_indices
            or completed_error_types
        ):
            timeout_workers = ",".join(
                str(index) for index in timed_out_indices
            ) or "none"
            incomplete_workers = ",".join(
                str(index) for index in incomplete_indices
            ) or "none"
            error_summary = ", ".join(
                sorted(completed_error_types)
            ) or "none"
            raise AssertionError(
                "Happy Cleaning worker failure; "
                f"timed_out={bool(timed_out_indices)}; "
                f"timed_out_workers={timeout_workers}; "
                f"incomplete_workers={incomplete_workers}; "
                "sanitized exception types: "
                f"{error_summary}"
            )

    def test_harness_reports_completed_worker_error_types(self):
        with self.assertRaises(AssertionError) as failure:
            self._assert_worker_health(
                timed_out_indices=(),
                completed_indices=(0, 1),
                completed_error_types=("RuntimeError",),
                expected_workers=2,
            )

        self.assertIn("timed_out=False", str(failure.exception))
        self.assertIn("RuntimeError", str(failure.exception))

    def test_harness_classifies_timeout_with_completed_errors(self):
        with self.assertRaises(AssertionError) as failure:
            self._assert_worker_health(
                timed_out_indices=(1,),
                completed_indices=(0,),
                completed_error_types=("ValueError",),
                expected_workers=2,
            )

        self.assertIn("timed_out=True", str(failure.exception))
        self.assertIn("timed_out_workers=1", str(failure.exception))
        self.assertIn("ValueError", str(failure.exception))

    def test_concurrent_event_create_allocates_distinct_contiguous_numbers(self):
        results = self.concurrent_posts(
            reverse("happy-cleaning-event-create-api"),
            [
                {"request_id": "race-create-a"},
                {"request_id": "race-create-b"},
            ],
        )

        self.assertEqual([status for status, _payload in results], [201, 201])
        self.assertEqual(
            list(HappyCleaning.objects.values_list("display_number", flat=True)),
            [1, 2],
        )

    def test_concurrent_station_reorders_accept_only_one_expected_revision(self):
        event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
            revision=1,
        )
        stations = [
            HappyCleaningStation.objects.create(
                happy_cleaning=event,
                name=name,
                max_kids=2,
                meeting_point="Treffpunkt",
                position=position,
            )
            for position, name in enumerate(("A", "B", "C"), start=1)
        ]
        results = self.concurrent_posts(
            reverse("happy-cleaning-station-reorder-api", args=[event.id]),
            [
                {
                    "request_id": "race-order-a",
                    "expected_revision": 1,
                    "station_ids": [stations[2].id, stations[1].id, stations[0].id],
                },
                {
                    "request_id": "race-order-b",
                    "expected_revision": 1,
                    "station_ids": [stations[1].id, stations[0].id, stations[2].id],
                },
            ],
        )

        self.assertCountEqual(
            [status for status, _payload in results],
            [200, 409],
        )
        self.assertEqual(
            [payload.get("code") for _status, payload in results].count("stale"),
            1,
        )
        self.assertEqual(
            list(HappyCleaningStation.objects.filter(
                happy_cleaning=event,
            ).values_list("position", flat=True)),
            [1, 2, 3],
        )

    def test_concurrent_updates_to_different_todos_both_succeed(self):
        event = HappyCleaning.objects.create(
            turnus=self.turnus, display_number=1, revision=1
        )
        station = HappyCleaningStation.objects.create(
            happy_cleaning=event,
            name="Speisesaal",
            max_kids=2,
            meeting_point="Tür",
            position=1,
        )
        todos = [
            CanonicalTask.objects.create(
                station=station,
                text=text,
                position=position,
            )
            for position, text in enumerate(("Tische", "Boden"), start=1)
        ]

        results = self.concurrent_posts(
            [
                reverse(
                    "happy-cleaning-todo-check-api",
                    args=(event.id, station.id, todo.id),
                )
                for todo in todos
            ],
            [
                {"request_id": f"race-todo-{todo.id}", "expected_version": 1}
                for todo in todos
            ],
        )

        self.assertEqual([status for status, _payload in results], [200, 200])
        self.assertEqual(
            list(CanonicalTask.objects.filter(station=station).values_list(
                "checked", "version"
            )),
            [(True, 2), (True, 2)],
        )
