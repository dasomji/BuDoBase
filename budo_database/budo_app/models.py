import re
import datetime
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save, post_delete
from django.contrib.auth.models import User
from phonenumber_field.modelfields import PhoneNumberField
from django_resized import ResizedImageField
import requests
from urllib.parse import urlparse, parse_qs

# Create your models here.


class Profil(models.Model):

    ROLLEN = (
        ("b", "Betreuer:in"),
        ("k", "Küche"),
        ("o", "Organisator"),
        ("f", "Freiwillige:r")
    )

    ESSEN = (
        ("ft", "Flexitarisch"),
        ("vt", "Vegetarisch"),
        ("vn", "Vegan")
    )

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profil")
    rufname = models.CharField(
        max_length=255, blank=True, default="", help_text="Wie willst du genannt werden?")
    telefonnummer = PhoneNumberField(blank=True)
    allergien = models.CharField(max_length=500, blank=True, default="")
    coffee = models.CharField(max_length=500, blank=True,
                              default="", help_text="Wie magst du deinen Kaffee?")
    rolle = models.CharField(
        max_length=1,
        choices=ROLLEN,
        blank=True,
        default="b",
        help_text="Was ist deine Rolle im Team?"
    )

    essen = models.CharField(
        max_length=2,
        choices=ESSEN,
        blank=True,
        default="ft",
        help_text="Was möchtest du essen?"
    )

    turnus = models.ForeignKey(
        "Turnus", on_delete=models.SET_NULL, null=True, blank=True, related_name="teamer"
    )

    class Meta:
        verbose_name_plural = "Profile"

    def __str__(self):
        return self.rufname

    def get_food(self):
        if self.essen == "ft":
            return "🥩 Flexitarisch"
        if self.essen == "vt":
            return "🧀 Vegetarisch"
        if self.essen == "vn":
            return "🥦 Vegan"

    def get_rolle(self):
        return dict(self.ROLLEN).get(self.rolle)

    def get_geld_sum(self):
        return sum(t.amount for t in self.betreuerinnen_geld.all())


class SpezialFamilien(models.Model):
    name = models.CharField(max_length=255)
    turnus = models.ForeignKey(
        "Turnus", on_delete=models.SET_NULL, null=True, blank=True, related_name="spezial_familien")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Spezialfamilien"


class Kinder(models.Model):
    BUDO_FAMILIES = [
        ("S", "Smallie"),
        ("M", "Medi"),
        ("L", "Largie"),
        ("XL", "X-largie"),
    ]

    WO_ABWESEND = [
        ("BuDo", 'BuDo'),
        ("Sallingstadt", "Sallingstadt"),
        ("Krankenhaus", "Krankenhaus"),
        ("Auslagern", "Auslagern"),
        ("Sonstiges", "Sonstiges")
    ]

    kid_index = models.CharField(max_length=255)
    kid_vorname = models.CharField(max_length=255)
    kid_nachname = models.CharField(max_length=255)
    kid_birthday = models.DateField(null=True, default=None)
    zug_anreise = models.BooleanField(null=True, default=None)
    zug_abreise = models.BooleanField(null=True, default=None)
    notiz_abreise = models.CharField(max_length=500, blank=True, default="")
    # script to filter for "kein Top Jugendticket vorhanden"
    top_jugendticket = models.BooleanField(null=True, default=None)
    # 1 oder 2 --> little script to convert
    turnus_dauer = models.IntegerField(null=True, default=None)
    geschwister = models.CharField(max_length=255, null=True)
    zeltwunsch = models.CharField(max_length=255, null=True)
    schimmkenntnisse = models.CharField(max_length=255, null=True)
    haftpflichtversicherung = models.CharField(max_length=255, null=True)
    budo_erfahrung = models.BooleanField(null=True)
    anmerkung_buchung = models.TextField(null=True, blank=True)
    anmerkung = models.TextField(null=True, blank=True)
    turnus = models.ForeignKey("Turnus", on_delete=models.SET_NULL, null=True)

    # familie
    anmelder_vorname = models.CharField(max_length=255)
    anmelder_nachname = models.CharField(max_length=255)
    anmelde_organisation = models.CharField(max_length=255, null=True)
    anmelder_email = models.CharField(max_length=255, null=True, default=None)
    anmelder_mobil = models.CharField(max_length=255, null=True)
    hauptversichert_bei = models.CharField(max_length=255, null=True)
    # rechnung
    rechnungsadresse = models.CharField(max_length=255)
    rechnung_plz = models.IntegerField(null=True, default=None)
    rechnung_ort = models.CharField(max_length=255)
    rechnung_land = models.CharField(max_length=255)
    notfall_kontakte = models.TextField(
        null=True, blank=True)  # import from rawdata

    # health

    sex = models.CharField(max_length=255, null=True, default=None, blank=True)
    sozialversicherungsnr = models.CharField(
        max_length=255, null=True, blank=True)
    tetanusimpfung = models.CharField(max_length=255, null=True, blank=True)
    zeckenimpfung = models.CharField(max_length=255, null=True, blank=True)
    vegetarisch = models.CharField(max_length=255, null=True, blank=True)
    special_food_description = models.CharField(
        max_length=255, null=True, blank=True)
    drugs = models.TextField(null=True, blank=True)
    illness = models.TextField(null=True, blank=True)
    rezeptfreie_medikamente = models.TextField(
        null=True, blank=True)
    rezept_medikamente = models.CharField(
        max_length=255, null=True, blank=True)
    swimmer = models.CharField(
        max_length=255, null=True, default=None, blank=True)
    covid = models.CharField(max_length=255, null=True, blank=True)

    # anwesenheit & budo-internes

    anwesend = models.BooleanField(null=True, default=None, blank=True)
    wo = models.CharField(max_length=20, choices=WO_ABWESEND,
                          default=None, null=True, blank=True)
    check_in_date = models.DateField(null=True, default=None, blank=True)
    ausweis = models.BooleanField(null=True, default=None, blank=True)
    e_card = models.BooleanField(null=True, default=None, blank=True)
    einverstaendnis_erklaerung = models.BooleanField(
        null=True, default=None, blank=True)
    taschengeld = models.CharField(
        max_length=20, null=True, default="", blank=True)
    budo_family = models.CharField(
        max_length=30, choices=BUDO_FAMILIES, null=True, blank=True)
    spezial_familien = models.ForeignKey(
        "SpezialFamilien", on_delete=models.SET_NULL, null=True, blank=True, related_name="kinder")
    late_anreise = models.DateField(null=True, blank=True)
    early_abreise_date = models.DateField(null=True, blank=True)
    early_abreise_abholer = models.CharField(
        max_length=255, null=True, blank=True)
    early_abreise_reason = models.CharField(
        max_length=255, null=True, blank=True)
    came_back = models.DateField(null=True, blank=True)
    anmerkung_team = models.CharField(
        max_length=1000, null=True, default="", blank=True)
    pfand = models.IntegerField(default=0)

    # Schwerpunkte & Familien
    schwerpunkte = models.ManyToManyField(
        'Schwerpunkte', blank=True, related_name="swp_kinder", verbose_name="Schwerpunkt")

    def get_alter(self):
        if self.kid_birthday is None:
            return None
        delta = self.turnus.turnus_beginn - self.kid_birthday
        age = round(delta.days / 365.25, 2)
        return age

    def is_birthday_during_turnus(self):
        if self.turnus and self.turnus.turnus_beginn:
            turnus_beginn = self.turnus.turnus_beginn
            turnus_ende = self.turnus.get_turnus_ende()

            # Create new dates for comparison by replacing the year of the birthday with the year of the turnus dates
            birthday_this_turnus = self.kid_birthday.replace(
                year=turnus_beginn.year)
            birthday_next_turnus = self.kid_birthday.replace(
                year=turnus_ende.year)

            # Check if the birthday falls within the turnus dates
            return turnus_beginn <= birthday_this_turnus <= turnus_ende or turnus_beginn <= birthday_next_turnus <= turnus_ende
        else:
            return False

    def __str__(self):
        return f'{self.kid_vorname} {self.kid_nachname}'

    def get_short_sex(self):
        if self.sex == "weiblich":
            return "♀"
        elif self.sex == "männlich":
            return "♂"
        else:
            return "d"

    def get_clean_special_food(self):
        if self.special_food_description:
            if self.special_food_description.lower() in ("nein", "keine", "keinr", "nan", "ja"):
                return ""
            else:
                return self.special_food_description

    def get_veggie(self):
        if self.vegetarisch:
            if self.vegetarisch.lower() == "ja":
                return "🥦"
            elif str(self.vegetarisch).lower().strip() in ("nein", "nan"):
                return "🥩"
            else:
                return self.vegetarisch
        else:
            return "🥩"

    def get_veggie_bool(self):
        if self.vegetarisch:
            if self.vegetarisch.lower() == "ja":
                return True
            else:
                return False
        else:
            return False

    def get_food(self):
        veggie = self.get_veggie()
        if self.special_food_description:
            if self.special_food_description.lower() in ("nein", "keine", "nan", "ja"):
                return veggie
            else:
                special = self.special_food_description
                return f"{veggie} - {special}"
        else:
            return veggie

    def get_clean_drugs(self):
        if self.drugs:
            if self.drugs.lower().strip() in ("nein", "nan", "none", "-"):
                return ""
            else:
                return self.drugs
        else:
            return ""

    def get_clean_illness(self):
        if self.illness:
            if self.illness.lower().strip() in ("nein", "nan", "none", "-"):
                return ""
            else:
                return self.illness
        else:
            return ""

    def get_clean_anmerkung(self):
        if self.anmerkung:
            if str(self.anmerkung).lower().strip() in ("nein", "nan", "none", "-", "0", "/"):
                return ""
            else:
                return self.anmerkung
        else:
            return ""

    def get_clean_anmerkung_buchung(self):
        if self.anmerkung_buchung:
            if str(self.anmerkung).lower().strip() in ("nein", "nan", "none", "-", "0", "/"):
                return ""
            elif self.anmerkung == 0:
                return ""
            else:
                return self.anmerkung_buchung
        else:
            return ""

    def get_clean_geschwister(self):
        if self.geschwister:
            if str(self.geschwister).lower().strip() in ("nein", "nan", "none", "-", "0", "bein"):
                return ""
            else:
                return self.geschwister
        else:
            return ""

    def get_clean_zeltwunsch(self):
        if self.zeltwunsch:
            if str(self.zeltwunsch).lower().strip() in ("nein", "nan", "none", "-", "0", "bein"):
                return ""
            else:
                return self.zeltwunsch
        else:
            return ""

    def get_zuganreise(self):
        if self.zug_anreise == True:
            return "Ja"
        else:
            return "Nein"

    def get_zugabreise(self):
        if self.zug_abreise == True:
            return "Ja"
        else:
            return "Nein"

    def get_topjugendticket(self):
        if self.top_jugendticket == True:
            return "Ja"
        else:
            return "Nein"

    def get_swp1(self):
        if self.schwerpunkte.filter(schwerpunktzeit__woche="w1").exists():
            return self.schwerpunkte.filter(schwerpunktzeit__woche="w1").first()
        else:
            return "---"

    def get_swp2(self):
        if self.schwerpunkte.filter(schwerpunktzeit__woche="w2").exists():
            return self.schwerpunkte.filter(schwerpunktzeit__woche="w2").first()
        else:
            return "---"

    def get_taschengeld_sum(self):
        return sum(t.amount for t in self.geld.all())

    def get_remaining_taschengeld(self):
        """Calculate remaining money after pfand deduction (0.25 per pfand)"""
        return self.get_taschengeld_sum() - (self.pfand * 0.25)

    @classmethod
    def get_zugabreise_count(cls, turnus=None):
        if turnus:
            return cls.objects.filter(zug_abreise=True, turnus=turnus).count()
        return cls.objects.filter(zug_abreise=True).count()

    @classmethod
    def get_zuganreise_count(cls, turnus=None):
        if turnus:
            return cls.objects.filter(zug_anreise=True, turnus=turnus).count()
        return cls.objects.filter(zug_anreise=True).count()

    class Meta:
        verbose_name_plural = "Kinder"
        indexes = [
            models.Index(fields=['turnus'], name='kinder_turnus_idx'),
            models.Index(fields=['kid_index'], name='kinder_kid_index_idx'),
            models.Index(fields=['anwesend'], name='kinder_anwesend_idx'),
            models.Index(fields=['turnus', 'anwesend'],
                         name='kinder_turnus_anwesend_idx'),
            models.Index(fields=['budo_family'],
                         name='kinder_budo_family_idx'),
            models.Index(
                fields=['kid_vorname', 'kid_nachname'], name='kinder_name_idx'),
        ]


class Notizen(models.Model):
    kinder = models.ForeignKey(
        Kinder, on_delete=models.CASCADE, related_name='notizen')
    notiz = models.TextField(null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.notiz

    def kids_name(self):
        return f"{self.kinder.kid_vorname} {self.kinder.kid_nachname}"

    class Meta:
        verbose_name_plural = "Notizen"


class Geld(models.Model):
    kinder = models.ForeignKey(
        Kinder, on_delete=models.CASCADE, related_name='geld')
    amount = models.FloatField(null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.amount} EUR"

    class Meta:
        verbose_name_plural = "Taschengeld"


class BetreuerinnenGeld(models.Model):
    amount = models.FloatField(null=True, blank=True)
    what = models.CharField(max_length=500)
    date_added = models.DateTimeField(auto_now_add=True)
    who = models.ForeignKey(Profil, on_delete=models.CASCADE,
                            related_name='betreuerinnen_geld')

    def __str__(self):
        return f"{self.amount} EUR - {self.what} - {self.who}"


class Turnus(models.Model):
    turnus_nr = models.IntegerField(null=True, default=None)
    turnus_beginn = models.DateField()
    uploadedFile = models.FileField(
        upload_to="Uploaded Files/", blank=True, null=True)
    dateTimeOfUpload = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'T{self.turnus_nr}-{self.turnus_beginn.year}'

    def save(self, *args, **kwargs):
        # If this is a new instance (i.e., it doesn't have an ID yet),
        # then we need to create the Schwerpunktzeit instances after saving.
        is_new = self.pk is None

        super().save(*args, **kwargs)

        if is_new:
            Schwerpunktzeit.objects.create(
                woche="w1",
                dauer=DayDuration.LANG,
                swp_beginn=self.turnus_beginn + timedelta(days=4),
                turnus=self
            )
            Schwerpunktzeit.objects.create(
                woche="w2",
                dauer=DayDuration.KURZ,
                swp_beginn=self.turnus_beginn + timedelta(days=8),
                turnus=self
            )

    def get_turnus_beginn_formatiert(self):
        return self.turnus_beginn.strftime("%d.%m.%Y")

    def get_upload_time(self):
        return self.dateTimeOfUpload.strftime("%H:%M am %d.%m.%Y")

    def get_turnus_ende(self):
        number_of_days = 13
        end_datum = self.turnus_beginn + \
            datetime.timedelta(days=number_of_days)
        return end_datum

    class Meta:
        verbose_name_plural = "Turnus"
        indexes = [
            models.Index(fields=['turnus_beginn'], name='turnus_beginn_idx'),
            models.Index(fields=['turnus_nr'], name='turnus_nr_idx'),
        ]


class Schwerpunkte(models.Model):
    swp_name = models.CharField(
        max_length=255, help_text="Was ist der Name des Schwerpunkts?", verbose_name="Schwerpunktname")
    ort = models.ForeignKey(
        "Auslagerorte", on_delete=models.SET_NULL, blank=True, null=True, help_text="Wo findet der Schwerpunkt statt?")
    betreuende = models.ManyToManyField(
        "Profil", blank=True, related_name="swp")
    beschreibung = models.TextField(blank=True)

    schwerpunktzeit = models.ForeignKey(
        "Schwerpunktzeit",
        related_name="swp",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    auslagern = models.BooleanField(null=True, default=None)
    geplante_abreise = models.DateTimeField(null=True, blank=True)
    geplante_ankunft = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.swp_name

    def get_betreuende_names(self):
        return ', '.join([betreuende.rufname for betreuende in self.betreuende.all()])

    def get_auslagern(self):
        if self.auslagern == True:
            return "Ja"
        else:
            return "Nein"

    def get_turnus(self):
        return self.schwerpunktzeit.turnus

    def get_essenseinteilung(self):
        return any(meal.meal_choice for meal in self.meals.all())

    def get_vegetarische_kids(self):
        return sum(1 for kid in self.swp_kinder.all() if kid.get_veggie_bool())

    def get_fleischkids(self):
        return sum(1 for kid in self.swp_kinder.all() if not kid.get_veggie_bool())

    def get_meals_by_day(self):
        meals_by_day = {}
        for meal in self.meals.all():
            if meal.day not in meals_by_day:
                meals_by_day[meal.day] = []
            meals_by_day[meal.day].append(meal)
        return meals_by_day

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Call the "real" save() method.
        schwerpunktzeit = self.schwerpunktzeit

        if schwerpunktzeit:
            # Get the current number of days for the meals
            current_days = self.meals.values_list('day', flat=True).distinct()

            # If the duration has changed, delete meals for days greater than the new duration
            if current_days and max(current_days) > schwerpunktzeit.dauer:
                self.meals.filter(day__gt=schwerpunktzeit.dauer).delete()

            # Create missing meals if the duration is longer
            for day in range(1, schwerpunktzeit.dauer + 1):
                for meal_type in ['breakfast', 'lunch', 'dinner']:
                    if not Meal.objects.filter(schwerpunkt=self, day=day, meal_type=meal_type).exists():
                        Meal.objects.create(
                            schwerpunkt=self, day=day, meal_type=meal_type)

    class Meta:
        verbose_name_plural = "Schwerpunkte"
        indexes = [
            models.Index(fields=['schwerpunktzeit'],
                         name='schwerpunkte_zeit_idx'),
            models.Index(fields=['ort'], name='schwerpunkte_ort_idx'),
            models.Index(fields=['auslagern'],
                         name='schwerpunkte_auslagern_idx'),
        ]


class Meal(models.Model):
    MEAL_TYPES = [
        ('breakfast', 'Frühstück'),
        ('lunch', 'Mittagessen'),
        ('dinner', 'Abendessen'),
    ]
    MEAL_CHOICES = [
        ('box', 'Box'),
        ('budo', 'Im BuDo'),
        ('warm', 'Warm geliefert'),
    ]
    schwerpunkt = models.ForeignKey(
        'Schwerpunkte', on_delete=models.CASCADE, related_name='meals')
    day = models.IntegerField()  # 1, 2, or 3
    meal_type = models.CharField(max_length=10, choices=MEAL_TYPES)
    meal_choice = models.CharField(
        max_length=10, choices=MEAL_CHOICES, blank=True)

    def __str__(self):
        return f"{self.schwerpunkt} Tag {self.day} {self.meal_type}"

    def get_kids_count(self):

        return self.schwerpunkt.swp_kinder.count()

    class Meta:
        # prevent duplicate meals
        unique_together = ('schwerpunkt', 'day', 'meal_type')


class DayDuration(models.IntegerChoices):
    SUPERKURZ = 1, '1 Tag - superkurz'
    KURZ = 2, '2 Tage - kurz'
    LANG = 3, '3 Tage - lang'
    SUPERLANG = 4, '4 Tage - superlang'


class Schwerpunktzeit(models.Model):
    WOCHEN_AUSWAHL = [
        ("w1", "Woche 1"),
        ("w2", "Woche 2"),
        ("u", "unklar")
    ]
    woche = models.CharField(
        max_length=2,
        choices=WOCHEN_AUSWAHL,
        default="u"
    )
    turnus = models.ForeignKey("Turnus", on_delete=models.CASCADE, null=True,
                               help_text="In welchem Turnus findet dieser Schwerpunkt statt?")
    swp_beginn = models.DateField()

    dauer = models.IntegerField(choices=DayDuration.choices)

    def __str__(self):
        if self.woche == "u":
            return self.get_woche_display()
        else:
            return f"{self.get_woche_display()} ({self.dauer} Tage) - {self.turnus}"

    class Meta:
        unique_together = ('turnus', 'woche')


class SchwerpunktWahl(models.Model):
    kind = models.ForeignKey(
        Kinder, on_delete=models.CASCADE, related_name='schwerpunkt_wahl')
    schwerpunktzeit = models.ForeignKey(
        Schwerpunktzeit, on_delete=models.CASCADE, related_name='wahlen')
    erste_wahl = models.ForeignKey(
        Schwerpunkte, on_delete=models.CASCADE, related_name='erste_wahl', null=True, blank=True)
    zweite_wahl = models.ForeignKey(
        Schwerpunkte, on_delete=models.CASCADE, related_name='zweite_wahl', null=True, blank=True)
    dritte_wahl = models.ForeignKey(
        Schwerpunkte, on_delete=models.CASCADE, related_name='dritte_wahl', null=True, blank=True)
    freunde = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        unique_together = ('kind', 'schwerpunktzeit')
        verbose_name = "Schwerpunkt Wahl"
        verbose_name_plural = "Schwerpunkt Wahlen"

    def __str__(self):
        return f"{self.kind} - {self.schwerpunktzeit}"

    # def clean(self):
    #     # Create a set of unique choices
    #     choices = set(
    #         filter(None, [self.erste_wahl, self.zweite_wahl, self.dritte_wahl]))

    #     # If the number of unique choices is less than the number of non-null choices,
    #     # it means there are duplicate choices
    #     if len(choices) < sum(1 for choice in [self.erste_wahl, self.zweite_wahl, self.dritte_wahl] if choice is not None):
    #         raise ValidationError(
    #             "Ein Schwerpunkt kann nicht mehrfach gewählt werden.")

    # def save(self, *args, **kwargs):
    #     self.clean()
    #     super().save(*args, **kwargs)


class Auslagerorte(models.Model):
    name = models.CharField(max_length=255)
    strasse = models.CharField(
        max_length=255, verbose_name="Straße", blank=True)
    ort = models.CharField(max_length=100, verbose_name="Stadt", blank=True)
    bundesland = models.CharField(
        max_length=100, verbose_name="Bundesland", blank=True)
    postleitzahl = models.CharField(
        max_length=20, verbose_name="Postleitzahl", blank=True)
    land = models.CharField(
        max_length=100, verbose_name="Land", default="Österreich", blank=True)
    koordinaten = models.CharField(max_length=255, blank=True, null=True)
    maps_link = models.URLField(blank=True, verbose_name="Google Maps Link")
    beschreibung = models.TextField(blank=True)
    kontakt = models.TextField(blank=True)
    maps_link_parkspot = models.URLField(
        blank=True, verbose_name="Google Maps Link Parkspot")
    koordinaten_parkspot = models.CharField(
        max_length=255, blank=True, null=True)

    def get_lat_ort(self):
        if self.koordinaten:
            return self.koordinaten.split(",")[0].strip()

    def get_lng_ort(self):
        if self.koordinaten:
            return self.koordinaten.split(",")[1].strip()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Auslagerorte"


class AuslagerorteImage(models.Model):
    auslagerort = models.ForeignKey(
        Auslagerorte, related_name='images', on_delete=models.CASCADE)
    image = ResizedImageField(
        size=[1080, 1080],
        force_format="jpeg",
        quality=75,
        upload_to='auslagerorte_images/'
    )


class AuslagerorteNotizen(models.Model):
    auslagerort = models.ForeignKey(
        Auslagerorte, on_delete=models.CASCADE, related_name='auslagernotizen')
    notiz = models.TextField(null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.notiz

    class Meta:
        verbose_name_plural = "Auslagerorte Notizen"


class Document(models.Model):
    title = models.CharField(max_length=200)
    uploadedFile = models.FileField(upload_to="Uploaded Files/")
    dateTimeOfUpload = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "Dokumente"


# These functions automatically create a Profil when a new user is created.
@receiver(post_save, sender=User)
def create_user_profil(sender, instance, created, **kwargs):
    if created:
        Profil.objects.create(
            user=instance, rufname=instance.username.capitalize())


@receiver(post_save, sender=User)
def save_user_profil(sender, instance, **kwargs):
    instance.profil.save()


@receiver(post_save, sender=Profil)
def invalidate_profile_cache(sender, instance, **kwargs):
    """Invalidate cached profile when it's updated"""
    from .utils import invalidate_user_profile_cache
    invalidate_user_profile_cache(instance.user)


# Cache invalidation for turnus data
@receiver(post_save, sender=Kinder)
@receiver(post_delete, sender=Kinder)
def invalidate_kinder_turnus_cache(sender, instance, **kwargs):
    """Invalidate turnus cache when Kinder data changes"""
    from .utils import invalidate_turnus_cache
    if instance.turnus:
        invalidate_turnus_cache(instance.turnus)


@receiver(post_save, sender=Schwerpunkte)
@receiver(post_delete, sender=Schwerpunkte)
def invalidate_schwerpunkte_turnus_cache(sender, instance, **kwargs):
    """Invalidate turnus cache when Schwerpunkte data changes"""
    from .utils import invalidate_turnus_cache
    if instance.schwerpunktzeit and instance.schwerpunktzeit.turnus:
        invalidate_turnus_cache(instance.schwerpunktzeit.turnus)


@receiver(post_save, sender=Auslagerorte)
@receiver(post_delete, sender=Auslagerorte)
def invalidate_auslagerorte_turnus_cache(sender, instance, **kwargs):
    """Invalidate turnus cache when Auslagerorte data changes"""
    from .utils import invalidate_all_turnus_caches
    # Auslagerorte can affect multiple turnuses, so invalidate all
    invalidate_all_turnus_caches()


@receiver(post_save, sender=Notizen)
@receiver(post_delete, sender=Notizen)
def invalidate_notizen_turnus_cache(sender, instance, **kwargs):
    """Invalidate turnus cache when Notizen data changes"""
    from .utils import invalidate_turnus_cache
    if instance.kinder and instance.kinder.turnus:
        invalidate_turnus_cache(instance.kinder.turnus)


@receiver(post_save, sender=Geld)
@receiver(post_delete, sender=Geld)
def invalidate_geld_turnus_cache(sender, instance, **kwargs):
    """Invalidate turnus cache when Geld data changes"""
    from .utils import invalidate_turnus_cache
    if instance.kinder and instance.kinder.turnus:
        invalidate_turnus_cache(instance.kinder.turnus)


def extract_coordinates_from_maps_link(url):
    try:
        # Expand the shortened URL
        response = requests.get(url, allow_redirects=True)
        full_url = response.url
        print(url)
        print(full_url)

        match = re.search(r'3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', full_url)
        if match:
            lat, lon = map(float, match.groups())
            return lat, lon
    except Exception as e:
        print(f"Error extracting coordinates: {e}")
    return None, None


@receiver(pre_save, sender=Auslagerorte)
def update_koordinaten(sender, instance, **kwargs):
    if instance.maps_link:
        lat, lon = extract_coordinates_from_maps_link(instance.maps_link)
        if lat and lon:
            instance.koordinaten = f"{lat},{lon}"

    if instance.maps_link_parkspot:
        lat_p, lon_p = extract_coordinates_from_maps_link(
            instance.maps_link_parkspot)
        if lat_p and lon_p:
            instance.koordinaten_parkspot = f"{lat_p},{lon_p}"
