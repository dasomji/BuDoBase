from django.db import models
from django.contrib.auth.models import User

# Create your models here.


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
    kid_alter = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, default=None)
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

    class AgeSorted:
        ordering = ('kid_alter')

    def __str__(self):
        return f'{self.kid_vorname} {self.kid_nachname} | {self.budo_family} | {self.kid_alter}'

    class Meta:
        verbose_name_plural = "Kinder"


class Notizen(models.Model):
    kinder = models.ForeignKey(
        Kinder, on_delete=models.CASCADE, related_name='notizen')
    notiz = models.TextField()
    date_added = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey("auth.User", on_delete=models.CASCADE)

    def __str__(self):
        return f"Notiz über {self.kinder.kid_vorname} {self.kinder.kid_nachname} von {self.added_by}: {self.notiz}"

    class Meta:
        verbose_name_plural = "Notizen"


class Turnus(models.Model):
    turnus_nr = models.IntegerField(null=True, default=None)
    turnus_year = models.IntegerField(null=True, default=None)
    uploadedFile = models.FileField(upload_to="Uploaded Files/")
    dateTimeOfUpload = models.DateField(auto_now=True)

    def __str__(self):
        return f'T{self.turnus_nr} {self.turnus_year}'

    class Meta:
        verbose_name_plural = "Turnus"


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
