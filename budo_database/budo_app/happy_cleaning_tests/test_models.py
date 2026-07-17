from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from budo_app.models import (
    HappyCleaning,
    HappyCleaningAssignment,
    HappyCleaningStation,
    HappyCleaningTodo,
    Kinder,
    Turnus,
)


class HappyCleaningModelTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 8, 1),
        )
        self.kid = Kinder.objects.create(
            kid_index="HC-1",
            kid_vorname="Ada",
            kid_nachname="Kind",
            turnus=self.turnus,
        )
        self.event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
        )
        self.station = HappyCleaningStation.objects.create(
            happy_cleaning=self.event,
            name="Speisesaal",
            max_kids=4,
            meeting_point="Vor dem Speisesaal",
            position=1,
        )

    def test_database_enforces_number_capacity_version_and_order_invariants(self):
        invalid_creates = (
            lambda: HappyCleaning.objects.create(
                turnus=self.turnus,
                display_number=0,
            ),
            lambda: HappyCleaning.objects.create(
                turnus=self.turnus,
                display_number=1,
            ),
            lambda: HappyCleaningStation.objects.create(
                happy_cleaning=self.event,
                name="Bad capacity",
                max_kids=0,
                meeting_point="Hier",
                position=2,
            ),
            lambda: HappyCleaningStation.objects.create(
                happy_cleaning=self.event,
                name="Duplicate position",
                max_kids=2,
                meeting_point="Hier",
                position=1,
            ),
            lambda: HappyCleaningTodo.objects.create(
                station=self.station,
                text="Invalid version",
                position=1,
                version=0,
            ),
        )

        for create in invalid_creates:
            with self.subTest(create=create), self.assertRaises(IntegrityError):
                with transaction.atomic():
                    create()

    def test_child_number_is_positive_and_unique_inside_its_turnus(self):
        self.kid.happy_cleaning_number = 17
        self.kid.save(update_fields=["happy_cleaning_number"])

        same_turnus_kid = Kinder.objects.create(
            kid_index="HC-2",
            kid_vorname="Grace",
            kid_nachname="Kind",
            turnus=self.turnus,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                same_turnus_kid.happy_cleaning_number = 17
                same_turnus_kid.save(update_fields=["happy_cleaning_number"])

        other_turnus_kid = Kinder.objects.create(
            kid_index="HC-3",
            kid_vorname="Linus",
            kid_nachname="Kind",
            turnus=self.other_turnus,
            happy_cleaning_number=17,
        )
        self.assertEqual(other_turnus_kid.happy_cleaning_number, 17)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                same_turnus_kid.happy_cleaning_number = 0
                same_turnus_kid.save(update_fields=["happy_cleaning_number"])

    def test_responsible_profile_and_assignment_references_validate_turnus(self):
        other_profile = User.objects.create_user(username="other-carer").profil
        other_profile.turnus = self.other_turnus
        other_profile.save(update_fields=["turnus"])

        self.station.responsible_profile = other_profile
        with self.assertRaises(ValidationError):
            self.station.full_clean()

        other_kid = Kinder.objects.create(
            kid_index="OTHER-1",
            kid_vorname="Other",
            kid_nachname="Kind",
            turnus=self.other_turnus,
        )
        assignment = HappyCleaningAssignment(
            happy_cleaning=self.event,
            station=self.station,
            child=other_kid,
        )
        with self.assertRaises(ValidationError):
            assignment.full_clean()

    def test_one_assignment_per_event_and_child_is_database_enforced(self):
        HappyCleaningAssignment.objects.create(
            happy_cleaning=self.event,
            station=self.station,
            child=self.kid,
        )
        second_station = HappyCleaningStation.objects.create(
            happy_cleaning=self.event,
            name="Küche",
            max_kids=2,
            meeting_point="Vor der Küche",
            position=2,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                HappyCleaningAssignment.objects.create(
                    happy_cleaning=self.event,
                    station=second_station,
                    child=self.kid,
                )

    def test_operational_markers_survive_assignment_removal_and_todo_reopen(self):
        assignment = HappyCleaningAssignment.objects.create(
            happy_cleaning=self.event,
            station=self.station,
            child=self.kid,
        )
        self.station.refresh_from_db()
        self.event.refresh_from_db()
        self.assertTrue(self.station.has_ever_had_assignment)
        self.assertTrue(self.event.has_operational_activity)

        assignment.delete()
        self.station.refresh_from_db()
        self.event.refresh_from_db()
        self.assertTrue(self.station.has_ever_had_assignment)
        self.assertTrue(self.event.has_operational_activity)

        second_event = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=2,
        )
        second_station = HappyCleaningStation.objects.create(
            happy_cleaning=second_event,
            name="Bad",
            max_kids=2,
            meeting_point="Vor dem Bad",
            position=1,
        )
        todo = HappyCleaningTodo.objects.create(
            station=second_station,
            text="Waschbecken putzen",
            position=1,
            checked=True,
        )
        second_event.refresh_from_db()
        self.assertTrue(second_event.has_operational_activity)

        todo.checked = False
        todo.save(update_fields=["checked"])
        second_event.refresh_from_db()
        self.assertTrue(second_event.has_operational_activity)

        second_event.has_operational_activity = False
        with self.assertRaises(ValidationError):
            second_event.save(update_fields=["has_operational_activity"])

    def test_default_ordering_is_stable(self):
        second_station = HappyCleaningStation.objects.create(
            happy_cleaning=self.event,
            name="Küche",
            max_kids=2,
            meeting_point="Vor der Küche",
            position=0,
        )
        later = HappyCleaningTodo.objects.create(
            station=self.station,
            text="Later",
            position=2,
        )
        earlier = HappyCleaningTodo.objects.create(
            station=self.station,
            text="Earlier",
            position=1,
        )

        self.assertEqual(
            list(self.event.stations.values_list("id", flat=True)),
            [second_station.id, self.station.id],
        )
        self.assertEqual(
            list(self.station.todos.values_list("id", flat=True)),
            [earlier.id, later.id],
        )
