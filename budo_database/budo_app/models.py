from django.db import models

# Create your models here.


class Kinder(models.Model):
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
        max_length=255, null=True, default=None)
    anmerkung = models.CharField(max_length=255, null=True)
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

    sex = models.CharField(max_length=255, null=True, default=None)
    sozialversicherungsnr = models.CharField(max_length=255, null=True)
    tetanusimpfung = models.CharField(max_length=255, null=True)
    zeckenimpfung = models.CharField(max_length=255, null=True)
    vegetarisch = models.CharField(max_length=255, null=True)
    special_food_description = models.CharField(max_length=255, null=True)
    drugs = models.CharField(max_length=255, null=True)
    illness = models.CharField(max_length=255, null=True)
    rezeptfreie_medikamente = models.CharField(max_length=255, null=True)
    rezept_medikamente = models.CharField(max_length=255, null=True)
    swimmer = models.CharField(max_length=255, null=True, default=None)
    covid = models.CharField(max_length=255, null=True)

    # anwesenheit

    anwesend = models.BooleanField(null=True, default=None)
    late_anreise = models.DateField(null=True)
    early_abreise_date = models.DateField(null=True)
    early_abreise_abholer = models.CharField(max_length=255, null=True)
    early_abreise_reason = models.CharField(max_length=255, null=True)
    came_back = models.DateField(null=True)
    anmerkung_team = models.CharField(max_length=1000, null=True, default="")

    # Schwerpunkte & Familien
    swp1 = models.ForeignKey(
        "SchwerpunktOne", on_delete=models.SET_NULL, null=True)
    swp2 = models.ForeignKey(
        "SchwerpunktTwo", on_delete=models.SET_NULL, null=True)
    # budo_family = create a new class with four options


class Turnus(models.Model):
    turnus_nr = models.IntegerField(null=True, default=None)
    turnus_year = models.IntegerField(null=True, default=None)
    uploadedFile = models.FileField(upload_to="Uploaded Files/")
    dateTimeOfUpload = models.DateField(auto_now=True)


class SchwerpunktOne(models.Model):
    swp_one_name = models.CharField(max_length=255, null=True)
    swp_one_auslagern = models.BooleanField(null=True, default=None)


class SchwerpunktTwo(models.Model):
    swp_two_name = models.CharField(max_length=255, null=True)
    swp_two_auslagern = models.BooleanField(null=True, default=None)


class Document(models.Model):
    title = models.CharField(max_length=200)
    uploadedFile = models.FileField(upload_to="Uploaded Files/")
    dateTimeOfUpload = models.DateTimeField(auto_now=True)
