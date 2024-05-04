from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import User
import datetime
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
    allergien = models.CharField(max_length=500, blank=True, default="")
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

    turnus = models.ManyToManyField(
        "Turnus", blank=True, related_name="teamer")

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
    # kid_alter = models.DecimalField(
    #     max_digits=4, decimal_places=2, null=True, default=None)
    kid_birthday = models.DateField(null=True, default=None)
    zug_anreise = models.BooleanField(null=True, default=None)
    zug_abreise = models.BooleanField(null=True, default=None)
    # script to filter for "kein Top Jugendticket vorhanden"
    top_jugendticket = models.BooleanField(null=True, default=None)
    # 1 oder 2 --> little script to convert
    turnus_dauer = models.IntegerField(null=True, default=None)
    geschwister = models.CharField(max_length=255, null=True)
    zeltwunsch = models.CharField(max_length=255, null=True)
    schimmkenntnisse = models.CharField(max_length=255, null=True)
    haftpflichtversicherung = models.CharField(max_length=255, null=True)
    budo_erfahrung = models.BooleanField(null=True)
    anmerkung_buchung = models.CharField(
        max_length=1000, null=True, default=None)
    anmerkung = models.CharField(max_length=1000, null=True)
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
    notfall_kontakte = models.CharField(
        max_length=255, null=True)  # import from rawdata

    # health

    sex = models.CharField(max_length=255, null=True, default=None, blank=True)
    sozialversicherungsnr = models.CharField(
        max_length=255, null=True, blank=True)
    tetanusimpfung = models.CharField(max_length=255, null=True, blank=True)
    zeckenimpfung = models.CharField(max_length=255, null=True, blank=True)
    vegetarisch = models.CharField(max_length=255, null=True, blank=True)
    special_food_description = models.CharField(
        max_length=255, null=True, blank=True)
    drugs = models.CharField(max_length=255, null=True, blank=True)
    illness = models.CharField(max_length=255, null=True, blank=True)
    rezeptfreie_medikamente = models.CharField(
        max_length=255, null=True, blank=True)
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
    late_anreise = models.DateField(null=True, blank=True)
    early_abreise_date = models.DateField(null=True, blank=True)
    early_abreise_abholer = models.CharField(
        max_length=255, null=True, blank=True)
    early_abreise_reason = models.CharField(
        max_length=255, null=True, blank=True)
    came_back = models.DateField(null=True, blank=True)
    anmerkung_team = models.CharField(
        max_length=1000, null=True, default="", blank=True)

    # Schwerpunkte & Familien
    schwerpunkt_woche1 = models.ForeignKey(
        'Schwerpunkte', on_delete=models.SET_NULL, null=True, related_name='kinder_woche1', blank=True, verbose_name="Schwerpunkt Woche 1")
    schwerpunkt_woche2 = models.ForeignKey(
        'Schwerpunkte', on_delete=models.SET_NULL, null=True, related_name='kinder_woche2', blank=True, verbose_name="Schwerpunkt Woche 2")

    # swp1 = models.ForeignKey(
    #     "SchwerpunktOne", on_delete=models.SET_NULL, null=True, blank=True)
    # swp2 = models.ForeignKey(
    #     "SchwerpunktTwo", on_delete=models.SET_NULL, null=True, blank=True)

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

    def get_food(self):
        veggie = ""
        if self.vegetarisch:
            if self.vegetarisch.lower() == "ja":
                veggie = "🥦"
            elif str(self.vegetarisch).lower().strip() in ("nein", "nan"):
                veggie = "🥩"
            else:
                veggie = self.vegetarisch
        else:
            veggie = "🥩"
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
            if str(self.anmerkung).lower().strip() in ("nein", "nan", "none", "-", "0"):
                return ""
            else:
                return self.anmerkung
        else: 
            return ""
        
    def get_clean_anmerkung_buchung(self):
        if self.anmerkung_buchung:
            if str(self.anmerkung).lower().strip() in ("nein", "nan", "none", "-", "0"):
                return ""
            else:
                return self.anmerkung_buchung
        else: 
            return ""    

    class Meta:
        verbose_name_plural = "Kinder"


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


class Turnus(models.Model):
    turnus_nr = models.IntegerField(null=True, default=None)
    turnus_beginn = models.DateField()
    uploadedFile = models.FileField(upload_to="Uploaded Files/")
    dateTimeOfUpload = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'T{self.turnus_nr}-{self.turnus_beginn.year}'

    class Meta:
        verbose_name_plural = "Turnus"

    def get_turnus_beginn_formatiert(self):
        return self.turnus_beginn.strftime("%d.%m.%Y")

    def get_upload_time(self):
        return self.dateTimeOfUpload.strftime("%H:%M am %d.%m.%Y")

    def get_turnus_ende(self):
        number_of_days = 13
        end_datum = self.turnus_beginn + \
            datetime.timedelta(days=number_of_days)
        return end_datum


class Schwerpunkte(models.Model):
    UNBEKANNT = "Unbekannt"
    WOCHE1 = "Woche 1"
    WOCHE2 = "Woche 2"
    WOCHEN_AUSWAHL = [
        (UNBEKANNT, "Unbekannt"),
        (WOCHE1, "Woche 1"),
        (WOCHE2, "Woche 2")
    ]
    swp_name = models.CharField(max_length=255)
    ort = models.ForeignKey(
        "Auslagerorte", on_delete=models.SET_NULL, blank=True, null=True)
    betreuende = models.ManyToManyField(
        "auth.User", blank=True)
    beschreibung = models.TextField()
    welche_woche = models.CharField(
        max_length=10,
        choices=WOCHEN_AUSWAHL,
        default=UNBEKANNT
    )
    auslagern = models.BooleanField(null=True, default=None)
    geplante_abreise = models.DateTimeField(null=True, blank=True)
    geplante_ankunft = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.swp_name

    class Meta:
        verbose_name_plural = "Schwerpunkte"


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
    koordinaten_parkspot = models.CharField(
        max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Auslagerorte"


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
