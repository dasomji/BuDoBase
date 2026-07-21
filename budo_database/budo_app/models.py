import datetime
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete, pre_delete, pre_save
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from phonenumber_field.modelfields import PhoneNumberField
from django_resized import ResizedImageField
from .first_aid_contract import OPAQUE_WEBP_KEY_PATTERN, SHA256_PATTERN
from .private_storage import attachment_storage
from .storage_lifecycle import (
    delete_field_file_on_commit,
    delete_storage_object_on_commit,
)
from .text_cleaning import (
    clean_optional_text,
    DEFAULT_EMPTY_VALUES,
    EXTENDED_EMPTY_VALUES,
    FOOD_EMPTY_VALUES,
    REQUEST_EMPTY_VALUES,
)

# Create your models here.


class Profil(models.Model):

    BUDO_FAMILIES = [
        ("S", "Smallie"),
        ("M", "Medi"),
        ("L", "Largie"),
        ("XL", "X-largie"),
    ]

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

    budo_family = models.CharField(
        max_length=2,
        choices=BUDO_FAMILIES,
        blank=True,
        default="",
        verbose_name="BuDo-Familie",
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
    happy_cleaning_number = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    happy_cleaning_number_version = models.PositiveIntegerField(default=1)

    # Schwerpunkte & Familien
    schwerpunkte = models.ManyToManyField(
        'Schwerpunkte', blank=True, related_name="swp_kinder", verbose_name="Schwerpunkt")

    def get_alter(self):
        if self.kid_birthday is None or self.turnus is None or self.turnus.turnus_beginn is None:
            return None
        delta = self.turnus.turnus_beginn - self.kid_birthday
        age = round(delta.days / 365.25, 2)
        return age

    def is_birthday_during_turnus(self):
        if self.kid_birthday and self.turnus and self.turnus.turnus_beginn:
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
        return clean_optional_text(self.special_food_description, FOOD_EMPTY_VALUES)

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
        return clean_optional_text(self.drugs, DEFAULT_EMPTY_VALUES)

    def get_clean_illness(self):
        return clean_optional_text(self.illness, DEFAULT_EMPTY_VALUES)

    def get_clean_anmerkung(self):
        return clean_optional_text(self.anmerkung, EXTENDED_EMPTY_VALUES)

    def get_clean_anmerkung_buchung(self):
        return clean_optional_text(self.anmerkung_buchung, EXTENDED_EMPTY_VALUES)

    def get_clean_geschwister(self):
        return clean_optional_text(self.geschwister, REQUEST_EMPTY_VALUES)

    def get_clean_zeltwunsch(self):
        return clean_optional_text(self.zeltwunsch, REQUEST_EMPTY_VALUES)

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
        return sum((transaction.amount or 0) for transaction in self.geld.all())

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
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(happy_cleaning_number__isnull=True)
                    | models.Q(happy_cleaning_number__gt=0)
                ),
                name="kinder_hc_number_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(happy_cleaning_number_version__gt=0),
                name="kinder_hc_number_version_positive",
            ),
            models.UniqueConstraint(
                fields=("turnus", "happy_cleaning_number"),
                condition=models.Q(happy_cleaning_number__isnull=False),
                name="kinder_turnus_hc_number_uniq",
            ),
        ]
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


class ErsteHilfeEintrag(models.Model):
    kinder = models.ForeignKey(
        Kinder,
        on_delete=models.CASCADE,
        related_name="erste_hilfe_eintraege",
    )
    beschreibung = models.TextField()
    date_added = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.beschreibung

    class Meta:
        verbose_name = "EH-Eintrag"
        verbose_name_plural = "EH-Einträge"


class AttachmentImage(models.Model):
    datei = models.FileField(
        storage=attachment_storage,
        validators=[
            RegexValidator(
                OPAQUE_WEBP_KEY_PATTERN,
                "Bilder benötigen einen opaken WebP-Speicherschlüssel.",
            ),
        ],
    )
    position = models.PositiveIntegerField()
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    checksum = models.CharField(
        max_length=64,
        validators=[
            RegexValidator(
                SHA256_PATTERN,
                "Die Prüfsumme muss ein kleingeschriebener SHA-256-Wert sein.",
            ),
        ],
    )

    class Meta:
        abstract = True
        ordering = ("position", "id")


class NotizFoto(AttachmentImage):
    eintrag = models.ForeignKey(
        Notizen,
        on_delete=models.CASCADE,
        related_name="fotos",
    )

    class Meta(AttachmentImage.Meta):
        verbose_name = "Notizfoto"
        verbose_name_plural = "Notizfotos"
        constraints = [
            models.UniqueConstraint(
                fields=("eintrag", "position"),
                name="notiz_foto_eintrag_position_uniq",
            ),
        ]


class ErsteHilfeFoto(AttachmentImage):
    eintrag = models.ForeignKey(
        ErsteHilfeEintrag,
        on_delete=models.CASCADE,
        related_name="fotos",
    )

    class Meta(AttachmentImage.Meta):
        verbose_name = "EH-Foto"
        verbose_name_plural = "EH-Fotos"
        constraints = [
            models.UniqueConstraint(
                fields=("eintrag", "position"),
                name="eh_foto_eintrag_position_uniq",
            ),
        ]


@receiver(pre_delete, sender=NotizFoto)
@receiver(pre_delete, sender=ErsteHilfeFoto)
def delete_attachment_file(sender, instance, **kwargs):
    """Delete transformed image bytes when admin/cascade removes their row."""
    delete_field_file_on_commit(instance.datei)


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


class HappyCleaning(models.Model):
    """One numbered Happy Cleaning event inside a Turnus."""

    turnus = models.ForeignKey(
        Turnus,
        on_delete=models.CASCADE,
        related_name="happy_cleanings",
    )
    display_number = models.PositiveIntegerField()
    revision = models.PositiveIntegerField(default=1)
    has_operational_activity = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if (
            self.pk
            and not self.has_operational_activity
            and type(self).objects.filter(
                pk=self.pk,
                has_operational_activity=True,
            ).exists()
        ):
            raise ValidationError(
                "Happy Cleaning activity markers cannot be reset."
            )
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Happy Cleaning {self.display_number} ({self.turnus})"

    class Meta:
        ordering = ("display_number", "id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(display_number__gt=0),
                name="happy_cleaning_number_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(revision__gt=0),
                name="happy_cleaning_revision_positive",
            ),
            models.UniqueConstraint(
                fields=("turnus", "display_number"),
                name="happy_cleaning_turnus_number_uniq",
            ),
        ]


class HappyCleaningCommandRequest(models.Model):
    """A completed Happy Cleaning command, retained for idempotent replay."""

    turnus = models.ForeignKey(
        Turnus,
        on_delete=models.CASCADE,
        related_name="happy_cleaning_command_requests",
    )
    actor_id = models.BigIntegerField()
    request_id = models.CharField(max_length=255)
    action = models.CharField(max_length=100)
    response = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("turnus", "actor_id", "request_id"),
                name="hc_command_actor_request_uniq",
            ),
        ]


class HappyCleaningStation(models.Model):
    happy_cleaning = models.ForeignKey(
        HappyCleaning,
        on_delete=models.CASCADE,
        related_name="stations",
    )
    name = models.CharField(max_length=255)
    max_kids = models.PositiveIntegerField()
    meeting_point = models.CharField(max_length=500)
    wishes = models.TextField(blank=True, default="")
    responsible_profile = models.ForeignKey(
        Profil,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="happy_cleaning_stations",
    )
    position = models.PositiveIntegerField()
    version = models.PositiveIntegerField(default=1)
    has_ever_had_assignment = models.BooleanField(default=False)

    def clean(self):
        super().clean()
        if (
            self.responsible_profile_id
            and self.happy_cleaning_id
            and self.responsible_profile.turnus_id
            != self.happy_cleaning.turnus_id
        ):
            raise ValidationError({
                "responsible_profile": (
                    "The responsible profile must belong to the station Turnus."
                ),
            })

    def save(self, *args, **kwargs):
        if (
            self.pk
            and not self.has_ever_had_assignment
            and type(self).objects.filter(
                pk=self.pk,
                has_ever_had_assignment=True,
            ).exists()
        ):
            raise ValidationError(
                "Station assignment markers cannot be reset."
            )
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ("position", "id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(max_kids__gt=0),
                name="hc_station_capacity_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(version__gt=0),
                name="hc_station_version_positive",
            ),
            models.UniqueConstraint(
                fields=("happy_cleaning", "position"),
                name="hc_station_event_position_uniq",
            ),
        ]


class HappyCleaningTodo(models.Model):
    station = models.ForeignKey(
        HappyCleaningStation,
        on_delete=models.CASCADE,
        related_name="todos",
    )
    text = models.CharField(max_length=500)
    position = models.PositiveIntegerField()
    checked = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)

    def save(self, *args, **kwargs):
        with transaction.atomic():
            result = super().save(*args, **kwargs)
            if self.checked:
                HappyCleaning.objects.filter(
                    pk=self.station.happy_cleaning_id,
                ).update(has_operational_activity=True)
            return result

    class Meta:
        ordering = ("position", "id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(version__gt=0),
                name="hc_todo_version_positive",
            ),
            models.UniqueConstraint(
                fields=("station", "position"),
                name="hc_todo_station_position_uniq",
            ),
        ]


class HappyCleaningAssignment(models.Model):
    happy_cleaning = models.ForeignKey(
        HappyCleaning,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    station = models.ForeignKey(
        HappyCleaningStation,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    child = models.ForeignKey(
        Kinder,
        on_delete=models.CASCADE,
        related_name="happy_cleaning_assignments",
    )
    version = models.PositiveIntegerField(default=1)

    def clean(self):
        super().clean()
        errors = {}
        if (
            self.station_id
            and self.happy_cleaning_id
            and self.station.happy_cleaning_id != self.happy_cleaning_id
        ):
            errors["station"] = (
                "The station must belong to the assignment Happy Cleaning."
            )
        if (
            self.child_id
            and self.happy_cleaning_id
            and self.child.turnus_id != self.happy_cleaning.turnus_id
        ):
            errors["child"] = (
                "The child must belong to the Happy Cleaning Turnus."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.clean()
        with transaction.atomic():
            result = super().save(*args, **kwargs)
            HappyCleaningStation.objects.filter(pk=self.station_id).update(
                has_ever_had_assignment=True,
            )
            HappyCleaning.objects.filter(pk=self.happy_cleaning_id).update(
                has_operational_activity=True,
            )
            return result

    class Meta:
        ordering = ("id",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(version__gt=0),
                name="hc_assignment_version_positive",
            ),
            models.UniqueConstraint(
                fields=("happy_cleaning", "child"),
                name="hc_assignment_event_child_uniq",
            ),
        ]


class ImmutableAuditEventQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Audit events are immutable.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValidationError("Audit events are immutable.")

    def bulk_create(
        self,
        objs,
        batch_size=None,
        ignore_conflicts=False,
        update_conflicts=False,
        update_fields=None,
        unique_fields=None,
    ):
        raise ValidationError("Audit events may only be created by the audit service.")

    def delete(self):
        raise ValidationError(
            "Audit events may only be deleted by Turnus retention."
        )


class AuditEventManager(models.Manager.from_queryset(ImmutableAuditEventQuerySet)):
    def _create_validated_event(self, **fields):
        event = self.model(**fields)
        event._audit_insert = True
        event.save(force_insert=True, using=self._db)
        return event


class AuditEvent(models.Model):
    """Immutable, Turnus-retained record written only by the audit service."""

    turnus = models.ForeignKey(
        Turnus,
        on_delete=models.CASCADE,
        related_name="audit_events",
    )
    actor_id = models.BigIntegerField(null=True, blank=True)
    actor_label = models.CharField(max_length=255)
    action = models.CharField(max_length=100)
    outcome = models.CharField(max_length=40)
    resource_type = models.CharField(max_length=100)
    resource_id = models.CharField(max_length=100)
    resource_label = models.CharField(max_length=255)
    request_id = models.CharField(max_length=255)
    occurred_at = models.DateTimeField(auto_now_add=True)
    client_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=1000, blank=True)
    details = models.JSONField(default=dict)

    objects = AuditEventManager()

    def save(self, *args, **kwargs):
        if not getattr(self, "_audit_insert", False) or self.pk is not None:
            raise ValidationError("Audit events are immutable.")
        try:
            return super().save(*args, **kwargs)
        finally:
            self._audit_insert = False

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "Audit events may only be deleted by Turnus retention."
        )

    class Meta:
        ordering = ("-occurred_at", "-id")
        permissions = (
            ("export_auditevent", "Can export audit events"),
        )
        indexes = [
            models.Index(
                fields=("turnus", "-occurred_at", "-id"),
                name="audit_turnus_time_idx",
            ),
            models.Index(
                fields=("turnus", "action"),
                name="audit_turnus_action_idx",
            ),
            models.Index(
                fields=("turnus", "resource_type", "resource_id"),
                name="audit_resource_idx",
            ),
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
    auslagern = models.BooleanField(default=False)

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
    notiz = models.ForeignKey(
        'AuslagerorteNotizen',
        related_name='images',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    image = ResizedImageField(
        size=[1080, 1080],
        force_format="JPEG",
        quality=75,
        keep_meta=True,
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
def remember_replaced_file(sender, instance, field_name):
    if not instance.pk:
        return

    try:
        previous = sender.objects.only(field_name).get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    previous_file = getattr(previous, field_name)
    current_file = getattr(instance, field_name)
    if previous_file.name and previous_file.name != current_file.name:
        instance._replaced_storage_file = (
            previous_file.storage,
            previous_file.name,
        )


@receiver(pre_save, sender=Turnus)
def remember_replaced_turnus_workbook(sender, instance, **kwargs):
    remember_replaced_file(sender, instance, "uploadedFile")


@receiver(pre_save, sender=Document)
def remember_replaced_document(sender, instance, **kwargs):
    remember_replaced_file(sender, instance, "uploadedFile")


@receiver(post_save, sender=Turnus)
@receiver(post_save, sender=Document)
def delete_replaced_file(sender, instance, **kwargs):
    replaced_file = getattr(instance, "_replaced_storage_file", None)
    if not replaced_file or getattr(
        instance, "_defer_replaced_file_cleanup", False
    ):
        return

    storage, name = replaced_file
    delete_storage_object_on_commit(storage, name)
    del instance._replaced_storage_file


@receiver(post_delete, sender=Turnus)
@receiver(post_delete, sender=Document)
def delete_uploaded_file(sender, instance, **kwargs):
    delete_field_file_on_commit(instance.uploadedFile)


@receiver(post_delete, sender=AuslagerorteImage)
def delete_location_image(sender, instance, **kwargs):
    delete_field_file_on_commit(instance.image)


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
@receiver(post_save, sender=ErsteHilfeEintrag)
@receiver(post_delete, sender=ErsteHilfeEintrag)
def invalidate_kid_activity_turnus_cache(sender, instance, **kwargs):
    """Invalidate turnus cache when notes or first-aid entries change."""
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
