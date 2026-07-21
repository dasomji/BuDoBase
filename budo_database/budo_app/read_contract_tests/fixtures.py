from datetime import date
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from budo_app.first_aid_tests.fixtures import create_first_aid_entry_for_test
from budo_app.models import (
    Auslagerorte,
    AuslagerorteImage,
    AuslagerorteNotizen,
    BetreuerinnenGeld,
    ErsteHilfeEintrag,
    Geld,
    Kinder,
    Notizen,
    Schwerpunkte,
    SchwerpunktWahl,
)


def image_upload(name):
    source = BytesIO()
    Image.new("RGB", (16, 16), "green").save(source, format="PNG")
    return SimpleUploadedFile(name, source.getvalue(), content_type="image/png")


class ActiveTurnusFixtureFactory:
    """Build cumulative small and realistic active-Turnus datasets."""

    def __init__(self, turnus, author):
        self.turnus = turnus
        self.author = author

    def grow_to(self, *, kids, focuses, team, places):
        self._grow_team(team)
        self._grow_places(places)
        self._grow_focuses(focuses)
        self._grow_kids(kids)

    def _grow_team(self, target):
        current = self.turnus.teamer.count()
        for index in range(current, target):
            user = User.objects.create_user(username=f"baseline-team-{index}")
            profile = user.profil
            profile.rufname = f"Teamer {index}"
            profile.turnus = self.turnus
            profile.allergien = "Nüsse" if index % 3 == 0 else ""
            profile.save()
            BetreuerinnenGeld.objects.create(
                who=profile,
                amount=10 + index,
                what=f"Einkauf {index}",
            )

    def _grow_places(self, target):
        current = Auslagerorte.objects.filter(
            name__startswith="Baseline Ort"
        ).count()
        for index in range(current, target):
            place = Auslagerorte.objects.create(
                name=f"Baseline Ort {index}",
                strasse=f"Waldweg {index}",
                ort="Sallingstadt",
                bundesland="Niederösterreich",
                postleitzahl="3931",
                koordinaten="48.5, 15.0",
                beschreibung=f"Beschreibung {index}",
                kontakt=f"Kontakt {index}",
            )
            AuslagerorteNotizen.objects.create(
                auslagerort=place,
                notiz=f"Ortsnotiz {index}",
                added_by=self.author,
            )
            AuslagerorteImage.objects.create(
                auslagerort=place,
                image=image_upload(f"baseline-place-{index}.png"),
            )

    def _grow_focuses(self, target):
        current = Schwerpunkte.objects.filter(
            schwerpunktzeit__turnus=self.turnus
        ).count()
        times = list(self.turnus.schwerpunktzeit_set.order_by("woche"))
        places = list(
            Auslagerorte.objects.filter(name__startswith="Baseline Ort").order_by("id")
        )
        team = list(self.turnus.teamer.order_by("id"))
        for index in range(current, target):
            focus = Schwerpunkte.objects.create(
                swp_name=f"Baseline Schwerpunkt {index}",
                beschreibung=f"Schwerpunktbeschreibung {index}",
                schwerpunktzeit=times[index % len(times)],
                ort=places[index % len(places)],
                auslagern=index % 2 == 0,
            )
            focus.betreuende.add(*team[:2])
            focus.meals.filter(day=1, meal_type="lunch").update(
                meal_choice="warm"
            )

    def _grow_kids(self, target):
        current = Kinder.objects.filter(turnus=self.turnus).count()
        focuses = list(
            Schwerpunkte.objects.filter(
                schwerpunktzeit__turnus=self.turnus
            ).order_by("id")
        )
        times = list(self.turnus.schwerpunktzeit_set.order_by("woche"))
        for index in range(current, target):
            kid = Kinder.objects.create(
                kid_index=f"BASE-{index:03d}",
                kid_vorname=f"Kind {index:03d}",
                kid_nachname="Baseline",
                kid_birthday=date(2012 + index % 4, 7, 2 + index % 10),
                turnus=self.turnus,
                turnus_dauer=2 if index % 4 else 1,
                anwesend=index % 3 != 0,
                zug_anreise=index % 2 == 0,
                zug_abreise=index % 3 == 0,
                sex="weiblich" if index % 2 else "männlich",
                vegetarisch="ja" if index % 4 == 0 else "nein",
                special_food_description="glutenfrei" if index % 7 == 0 else "",
                drugs="Asthmaspray" if index % 11 == 0 else "",
                illness="Allergie" if index % 13 == 0 else "",
                notfall_kontakte=f"Kontaktperson {index}",
                anmelder_vorname="Eltern",
                anmelder_nachname=f"Baseline {index}",
                anmelder_email=f"eltern-{index}@example.test",
                rechnungsadresse=f"Teststraße {index}",
                rechnung_ort="Wien",
                rechnung_land="AT",
                pfand=index % 5,
            )
            focus = focuses[index % len(focuses)]
            kid.schwerpunkte.add(focus)
            focus_time = times[index % len(times)]
            choices = [
                candidate
                for candidate in focuses
                if candidate.schwerpunktzeit_id == focus_time.id
            ][:3]
            SchwerpunktWahl.objects.create(
                kind=kid,
                schwerpunktzeit=focus_time,
                erste_wahl=choices[0] if choices else None,
                zweite_wahl=choices[1] if len(choices) > 1 else None,
                dritte_wahl=choices[2] if len(choices) > 2 else None,
                freunde=f"Freund {index}",
            )
            for item in range(2):
                Notizen.objects.create(
                    kinder=kid,
                    notiz=f"Notiz {item} für Kind {index}",
                    added_by=self.author,
                )
                create_first_aid_entry_for_test(
                    kinder=kid,
                    beschreibung=f"EH-Eintrag {item} für Kind {index}",
                    added_by=self.author,
                )
                Geld.objects.create(
                    kinder=kid,
                    amount=20 if item == 0 else -2.5,
                    added_by=self.author,
                )
