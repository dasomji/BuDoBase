import re
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from budo_app.kid_edit_contracts import (
    FIELD_CONTRACTS,
    canonicalize_storage_value,
    verify_field_baseline,
    verify_legacy_preserve_value,
    verify_swp_baseline,
)
from budo_app.memberships import create_membership, select_turnus
from budo_app.models import (
    AuditEvent,
    HappyCleaning,
    HappyCleaningAssignment,
    HappyCleaningCommandRequest,
    HappyCleaningStation,
    Kinder,
    Schwerpunkte,
    Turnus,
)


FIELD_NAMES = tuple(field.api_name for field in FIELD_CONTRACTS)
TOKEN = re.compile(r"\Av1\.[A-Za-z0-9_-]{43}\Z")
LEGACY_TOKEN = re.compile(r"\Alegacy:v1\.[A-Za-z0-9_-]{43}\Z")

FIELD_OPTIONS = {
    "sex": [
        {"value": None, "label": "Nicht angegeben"},
        {"value": "female", "label": "weiblich"},
        {"value": "male", "label": "männlich"},
        {"value": "diverse", "label": "divers"},
    ],
    "stay_weeks": [
        {"value": None, "label": "Nicht angegeben"},
        {"value": 1, "label": "1 Woche"},
        {"value": 2, "label": "2 Wochen"},
    ],
    "budo_experience": [
        {"value": None, "label": "Unbekannt"},
        {"value": True, "label": "Ja"},
        {"value": False, "label": "Nein"},
    ],
    "vegetarian": [
        {"value": None, "label": "Unbekannt"},
        {"value": True, "label": "Ja"},
        {"value": False, "label": "Nein"},
    ],
    "consent": [
        {"value": None, "label": "Unbekannt"},
        {"value": True, "label": "Ja"},
        {"value": False, "label": "Nein"},
    ],
    "budo_family": [
        {"value": None, "label": "Nicht zugeordnet"},
        {"value": "S", "label": "Smallie"},
        {"value": "M", "label": "Medi"},
        {"value": "L", "label": "Largie"},
        {"value": "XL", "label": "X-largie"},
    ],
}


class KidEditReadContractTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=163,
            turnus_beginn=date(2026, 7, 1),
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=164,
            turnus_beginn=date(2026, 8, 1),
        )
        self.user = User.objects.create_user(
            username="kid-edit-reader",
            password="secret",
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.save(update_fields=["turnus"])
        create_membership(user=self.user, turnus=self.turnus)
        select_turnus(self.user, self.turnus)
        self.client.force_login(self.user)
        self.kid = Kinder.objects.create(
            kid_index="SYNTHETIC-163-05",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            kid_birthday=date(2012, 7, 2),
            turnus=self.turnus,
            edit_version=4,
            happy_cleaning_number=42,
            happy_cleaning_number_version=3,
            sex="weiblich",
            turnus_dauer=2,
            geschwister="Charles",
            zeltwunsch="Grace",
            budo_erfahrung=True,
            sozialversicherungsnr="0207121234",
            illness="Allergie",
            drugs="Asthmaspray",
            vegetarisch="ja",
            special_food_description="Keine Nüsse",
            swimmer="gut",
            einverstaendnis_erklaerung=True,
            rezeptfreie_medikamente="Ibuprofen",
            rezept_medikamente="Spray",
            tetanusimpfung="2023",
            zeckenimpfung="Grundimmunisiert",
            anmelde_organisation="Ferienverein",
            anmelder_vorname="Ann",
            anmelder_nachname="Lovelace",
            anmelder_email="ann@example.test",
            anmelder_mobil="+43 660 123",
            hauptversichert_bei="Ann Lovelace",
            notfall_kontakte="Grace\n+43 660 456",
            budo_family="M",
        )
        self.foreign_kid = Kinder.objects.create(
            kid_index="SYNTHETIC-FOREIGN-163-05",
            kid_vorname="Foreign",
            kid_nachname="Child",
            turnus=self.other_turnus,
            illness="FOREIGN-PRIVATE-VALUE",
        )

        self.period_w1 = self.turnus.schwerpunktzeit_set.get(woche="w1")
        self.period_w2 = self.turnus.schwerpunktzeit_set.get(woche="w2")
        self.period_w1.swp_beginn = date(2026, 7, 8)
        self.period_w1.dauer = 3
        self.period_w1.save(update_fields=["swp_beginn", "dauer"])
        self.period_w2.swp_beginn = date(2026, 7, 2)
        self.period_w2.dauer = 2
        self.period_w2.save(update_fields=["swp_beginn", "dauer"])
        self.alpha_lower = Schwerpunkte.objects.create(
            swp_name="alpha",
            schwerpunktzeit=self.period_w1,
        )
        self.alpha_upper = Schwerpunkte.objects.create(
            swp_name="Alpha",
            schwerpunktzeit=self.period_w1,
        )
        self.zeta = Schwerpunkte.objects.create(
            swp_name="zeta",
            schwerpunktzeit=self.period_w1,
        )
        self.w2_focus = Schwerpunkte.objects.create(
            swp_name="Wald",
            schwerpunktzeit=self.period_w2,
        )
        self.kid.schwerpunkte.add(self.alpha_lower)

        self.event_two = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=2,
            revision=4,
        )
        self.event_one = HappyCleaning.objects.create(
            turnus=self.turnus,
            display_number=1,
            revision=9,
        )
        self.other_event = HappyCleaning.objects.create(
            turnus=self.other_turnus,
            display_number=1,
            revision=99,
        )
        self.full_station = HappyCleaningStation.objects.create(
            happy_cleaning=self.event_one,
            name="Andere volle Station",
            max_kids=1,
            meeting_point="Synthetic",
            position=1,
        )
        self.current_station = HappyCleaningStation.objects.create(
            happy_cleaning=self.event_one,
            name="Aktuelle überbuchte Station",
            max_kids=1,
            meeting_point="Synthetic",
            position=2,
        )
        self.empty_station = HappyCleaningStation.objects.create(
            happy_cleaning=self.event_two,
            name="Leere Station",
            max_kids=3,
            meeting_point="Synthetic",
            position=1,
        )
        self.foreign_station = HappyCleaningStation.objects.create(
            happy_cleaning=self.other_event,
            name="FOREIGN-STATION-LABEL",
            max_kids=100,
            meeting_point="Foreign",
            position=1,
        )
        other_children = [
            Kinder.objects.create(
                kid_index=f"SYNTHETIC-CAPACITY-{index}",
                kid_vorname=f"Capacity{index}",
                kid_nachname="Child",
                turnus=self.turnus,
            )
            for index in range(3)
        ]
        HappyCleaningAssignment.objects.create(
            happy_cleaning=self.event_one,
            station=self.full_station,
            child=other_children[0],
            version=2,
        )
        HappyCleaningAssignment.objects.create(
            happy_cleaning=self.event_one,
            station=self.current_station,
            child=self.kid,
            version=11,
        )
        HappyCleaningAssignment.objects.create(
            happy_cleaning=self.event_one,
            station=self.current_station,
            child=other_children[1],
            version=3,
        )

    def url(self, kid_id=None):
        path = reverse(
            "route-data-api",
            kwargs={"contract_key": "kid-edit"},
        )
        if kid_id is None:
            return path
        return f"{path}?id={kid_id}"

    def get_kid(self):
        response = self.client.get(self.url(self.kid.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"kid"})
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        return response, response.json()["kid"]

    def test_exact_ordinary_projection_baselines_and_six_option_groups(self):
        _response, kid = self.get_kid()
        self.assertEqual(
            set(kid),
            {
                "id",
                "full_name",
                "edit_version",
                "fields",
                "field_options",
                "field_baselines",
                "happy_cleaning_number",
                "swp_periods",
                "happy_cleaning_events",
            },
        )
        self.assertEqual(kid["id"], self.kid.id)
        self.assertEqual(kid["full_name"], "Ada Lovelace")
        self.assertEqual(kid["edit_version"], 4)
        self.assertEqual(tuple(kid["fields"]), FIELD_NAMES)
        self.assertEqual(tuple(kid["field_baselines"]), FIELD_NAMES)
        self.assertEqual(
            kid["fields"],
            {
                "first_name": "Ada",
                "last_name": "Lovelace",
                "sex": "female",
                "birthday": "2012-07-02",
                "stay_weeks": 2,
                "siblings": "Charles",
                "tent_request": "Grace",
                "budo_experience": True,
                "social_security_number": "0207121234",
                "illness": "Allergie",
                "drugs": "Asthmaspray",
                "vegetarian": True,
                "special_food": "Keine Nüsse",
                "swimmer": "gut",
                "consent": True,
                "over_the_counter_medication": "Ibuprofen",
                "prescription_medication": "Spray",
                "tetanus": "2023",
                "tick_vaccine": "Grundimmunisiert",
                "organization": "Ferienverein",
                "registrant_first_name": "Ann",
                "registrant_last_name": "Lovelace",
                "registrant_email": "ann@example.test",
                "registrant_phone": "+43 660 123",
                "insured_with": "Ann Lovelace",
                "emergency_contacts": "Grace\n+43 660 456",
                "budo_family": "M",
            },
        )
        self.assertEqual(kid["field_options"], FIELD_OPTIONS)
        self.assertEqual(
            kid["happy_cleaning_number"],
            {"value": 42, "version": 3},
        )
        for field in FIELD_CONTRACTS:
            token = kid["field_baselines"][field.api_name]
            self.assertRegex(token, TOKEN)
            raw = getattr(self.kid, field.storage_name)
            self.assertTrue(
                verify_field_baseline(
                    token,
                    turnus_id=self.turnus.id,
                    child_id=self.kid.id,
                    field_name=field.api_name,
                    canonical_value=canonicalize_storage_value(
                        field,
                        raw,
                    ).api_value,
                )
            )

    def test_periods_focus_options_targets_and_baselines_are_complete_ordered(self):
        _response, kid = self.get_kid()
        periods = kid["swp_periods"]
        self.assertEqual(
            tuple(period["id"] for period in periods),
            (self.period_w2.id, self.period_w1.id),
        )
        self.assertEqual(
            set(periods[0]),
            {
                "id",
                "code",
                "label",
                "start",
                "duration_days",
                "baseline",
                "target",
                "options",
            },
        )
        self.assertEqual(
            periods[0],
            {
                "id": self.period_w2.id,
                "code": "w2",
                "label": "Woche 2 (2 Tage)",
                "start": "2026-07-02",
                "duration_days": 2,
                "baseline": periods[0]["baseline"],
                "target": {"kind": "unassigned"},
                "options": [
                    {"target": {"kind": "unassigned"}, "label": "Nicht eingeteilt"},
                    {"target": {"kind": "focus", "focus_id": self.w2_focus.id}, "label": "Wald"},
                ],
            },
        )
        self.assertEqual(
            periods[1]["options"],
            [
                {"target": {"kind": "unassigned"}, "label": "Nicht eingeteilt"},
                {"target": {"kind": "focus", "focus_id": self.alpha_lower.id}, "label": "alpha"},
                {"target": {"kind": "focus", "focus_id": self.alpha_upper.id}, "label": "Alpha"},
                {"target": {"kind": "focus", "focus_id": self.zeta.id}, "label": "zeta"},
            ],
        )
        self.assertEqual(
            periods[1]["target"],
            {"kind": "focus", "focus_id": self.alpha_lower.id},
        )
        for period, current_ids in zip(periods, ((), (self.alpha_lower.id,))):
            self.assertRegex(period["baseline"], TOKEN)
            self.assertTrue(
                verify_swp_baseline(
                    period["baseline"],
                    turnus_id=self.turnus.id,
                    child_id=self.kid.id,
                    period_id=period["id"],
                    current_focus_ids=current_ids,
                )
            )

    def test_events_stations_capacity_and_current_selectability_are_exact(self):
        _response, kid = self.get_kid()
        events = kid["happy_cleaning_events"]
        self.assertEqual(
            tuple(event["id"] for event in events),
            (self.event_one.id, self.event_two.id),
        )
        first = events[0]
        self.assertEqual(
            set(first),
            {
                "id",
                "display_number",
                "label",
                "revision",
                "assignment_version",
                "target",
                "options",
            },
        )
        self.assertEqual(first["display_number"], 1)
        self.assertEqual(first["label"], "Happy Cleaning 1")
        self.assertEqual(first["revision"], 9)
        self.assertEqual(first["assignment_version"], 11)
        self.assertEqual(
            first["target"],
            {"kind": "station", "station_id": self.current_station.id},
        )
        self.assertEqual(
            first["options"][:2],
            [
                {"target": {"kind": "unassigned"}, "label": "Nicht eingeteilt", "can_select": True},
                {"target": {"kind": "excused"}, "label": "Entschuldigt", "can_select": True},
            ],
        )
        full, current = first["options"][2:]
        station_option_keys = {
            "target",
            "label",
            "station_id",
            "station_name",
            "position",
            "max_kids",
            "assigned_count",
            "free_seats",
            "overbooked_count",
            "can_select",
            "is_current",
        }
        self.assertEqual(set(full), station_option_keys)
        self.assertEqual(
            full["target"],
            {"kind": "station", "station_id": self.full_station.id},
        )
        self.assertEqual(full["label"], "Andere volle Station · 1/1 (voll)")
        self.assertEqual(
            {key: full[key] for key in (
                "station_id", "station_name", "position", "max_kids",
                "assigned_count", "free_seats", "overbooked_count",
                "can_select", "is_current",
            )},
            {
                "station_id": self.full_station.id,
                "station_name": "Andere volle Station",
                "position": 1,
                "max_kids": 1,
                "assigned_count": 1,
                "free_seats": 0,
                "overbooked_count": 0,
                "can_select": False,
                "is_current": False,
            },
        )
        self.assertEqual(set(current), station_option_keys)
        self.assertEqual(
            current["target"],
            {"kind": "station", "station_id": self.current_station.id},
        )
        self.assertEqual(
            current["label"],
            "Aktuelle überbuchte Station · 2/1",
        )
        self.assertEqual(
            {key: current[key] for key in (
                "station_id", "station_name", "position", "max_kids",
                "assigned_count", "free_seats", "overbooked_count",
                "can_select", "is_current",
            )},
            {
                "station_id": self.current_station.id,
                "station_name": "Aktuelle überbuchte Station",
                "position": 2,
                "max_kids": 1,
                "assigned_count": 2,
                "free_seats": 0,
                "overbooked_count": 1,
                "can_select": True,
                "is_current": True,
            },
        )
        self.assertEqual(events[1]["assignment_version"], 0)
        self.assertEqual(events[1]["target"], {"kind": "unassigned"})
        self.assertEqual(events[1]["display_number"], 2)
        self.assertEqual(events[1]["label"], "Happy Cleaning 2")
        self.assertEqual(events[1]["revision"], 4)
        self.assertEqual(
            events[1]["options"][:2],
            [
                {"target": {"kind": "unassigned"}, "label": "Nicht eingeteilt", "can_select": True},
                {"target": {"kind": "excused"}, "label": "Entschuldigt", "can_select": True},
            ],
        )
        self.assertEqual(len(events[1]["options"]), 3)
        empty = events[1]["options"][2]
        self.assertEqual(set(empty), station_option_keys)
        self.assertEqual(
            empty["target"],
            {"kind": "station", "station_id": self.empty_station.id},
        )
        self.assertEqual(empty["label"], "Leere Station · 0/3")
        self.assertEqual(
            {key: empty[key] for key in (
                "station_id", "station_name", "position", "max_kids",
                "assigned_count", "free_seats", "overbooked_count",
                "can_select", "is_current",
            )},
            {
                "station_id": self.empty_station.id,
                "station_name": "Leere Station",
                "position": 1,
                "max_kids": 3,
                "assigned_count": 0,
                "free_seats": 3,
                "overbooked_count": 0,
                "can_select": True,
                "is_current": False,
            },
        )

    def test_corrupt_foreign_station_assignment_fails_closed_without_leakage(self):
        HappyCleaningAssignment.objects.filter(
            happy_cleaning=self.event_one,
            child=self.kid,
        ).update(station_id=self.foreign_station.id)

        response, kid = self.get_kid()

        event = next(
            item
            for item in kid["happy_cleaning_events"]
            if item["id"] == self.event_one.id
        )
        self.assertEqual(event["target"], {"kind": "unassigned"})
        self.assertEqual(event["assignment_version"], 0)
        self.assertNotIn(
            self.foreign_station.id,
            [
                option["target"].get("station_id")
                for projected_event in kid["happy_cleaning_events"]
                for option in projected_event["options"]
            ] + [
                projected_event["target"].get("station_id")
                for projected_event in kid["happy_cleaning_events"]
            ],
        )
        self.assertNotContains(response, "FOREIGN-STATION-LABEL")

    def test_legacy_values_multilinks_and_foreign_relations_are_preserved_safely(self):
        Kinder.objects.filter(pk=self.kid.id).update(
            sex="Legacy <sex>",
            anmelder_email="  ada@  ",
            illness="  NEIN  ",
        )
        self.kid.refresh_from_db()
        self.kid.schwerpunkte.add(self.alpha_upper)
        foreign_focus = Schwerpunkte.objects.create(
            swp_name="FOREIGN-FOCUS-LABEL",
            schwerpunktzeit=self.other_turnus.schwerpunktzeit_set.get(woche="w1"),
        )
        self.kid.schwerpunkte.add(foreign_focus)

        response, kid = self.get_kid()
        legacy_value = kid["fields"]["sex"]
        self.assertRegex(legacy_value, LEGACY_TOKEN)
        self.assertEqual(
            kid["field_options"]["sex"][0],
            {"value": legacy_value, "label": "Bisher: Legacy <sex>", "legacy": True},
        )
        self.assertTrue(
            verify_legacy_preserve_value(
                legacy_value,
                turnus_id=self.turnus.id,
                child_id=self.kid.id,
                field_name="sex",
                raw_storage_value="Legacy <sex>",
            )
        )
        self.assertEqual(kid["fields"]["registrant_email"], "ada@")
        self.assertEqual(kid["fields"]["illness"], "")
        w1 = next(item for item in kid["swp_periods"] if item["id"] == self.period_w1.id)
        submitted_target = {
            "kind": "preserve_legacy",
            "token": w1["baseline"],
        }
        legacy_label = "Bisher: alpha + Alpha (Mehrfachzuordnung)"
        self.assertEqual(
            w1["target"],
            {**submitted_target, "label": legacy_label},
        )
        preserve_options = [
            option for option in w1["options"]
            if option["target"] == submitted_target
        ]
        self.assertEqual(
            preserve_options,
            [{
                "target": submitted_target,
                "label": legacy_label,
                "legacy": True,
            }],
        )
        self.assertNotContains(response, "FOREIGN-FOCUS-LABEL")
        self.assertNotContains(response, "FOREIGN-STATION-LABEL")
        self.assertNotContains(response, "FOREIGN-PRIVATE-VALUE")

    def test_zero_periods_and_events_return_complete_empty_arrays(self):
        self.turnus.schwerpunktzeit_set.all().delete()
        self.turnus.happy_cleanings.all().delete()
        _response, kid = self.get_kid()
        self.assertEqual(kid["swp_periods"], [])
        self.assertEqual(kid["happy_cleaning_events"], [])

    def test_authentication_active_turnus_and_child_scope_are_indistinguishable(self):
        foreign = self.client.get(self.url(self.foreign_kid.id))
        missing = self.client.get(self.url(999_999_999))
        missing_id = self.client.get(self.url())
        self.user.turnus_memberships.all().delete()
        no_turnus = self.client.get(self.url(self.kid.id))
        for response in (foreign, missing, missing_id, no_turnus):
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json(), foreign.json())
            self.assertNotContains(response, "Foreign", status_code=404)

        self.client.logout()
        unauthenticated = self.client.get(self.url(self.kid.id))
        self.assertEqual(unauthenticated.status_code, 403)

    def test_contract_is_read_only_and_creates_no_audit_or_ledger_rows(self):
        before = {
            "kids": Kinder.objects.count(),
            "assignments": HappyCleaningAssignment.objects.count(),
            "audit": AuditEvent.objects.count(),
            "ledger": HappyCleaningCommandRequest.objects.count(),
        }
        get = self.client.get(self.url(self.kid.id))
        post = self.client.post(
            self.url(self.kid.id),
            data='{"synthetic":true}',
            content_type="application/json",
        )
        self.assertEqual(get.status_code, 200)
        self.assertEqual(post.status_code, 405)
        self.assertEqual(
            {
                "kids": Kinder.objects.count(),
                "assignments": HappyCleaningAssignment.objects.count(),
                "audit": AuditEvent.objects.count(),
                "ledger": HappyCleaningCommandRequest.objects.count(),
            },
            before,
        )
