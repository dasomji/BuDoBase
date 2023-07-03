import pandas as pd
# from budo_app.models import Turnus


from budo_app.models import Turnus, Kinder


def process():
    turnus = Turnus.objects.first()
    path = turnus.uploadedFile.url
    budo = pd.read_excel(open(path, "rb"), sheet_name="DataCleaner", header=1)
    for i in range(0, len(budo)):
        # turn Anreise string into boolean, True = Zuganreise
        if "Betreute Anreise" in budo["AnreiseText"][i]:
            kid_anreise = True
        else:
            kid_anreise = False
        # turn Abreise string into boolean, True = Zugabreise
        if "Betreute Abreise" in budo["AbreiseText"][i]:
            kid_abreise = True
        else:
            kid_abreise = False
        # extract from Abreise and Anreise if kid has Top Jugendticket
        if ", Top Jugendticket ist vorhanden" in budo["AnreiseText"][i] or ", Top Jugendticket ist vorhanden" in budo["AbreiseText"][i]:
            kid_jugendticket = True
        else:
            kid_jugendticket = False
        # extract from Turnusdauer if kid stays one or two weeks
        if "ganz" in budo["Turnusdauer"][i]:
            kid_dauer = 2
        else:
            kid_dauer = 1

        # boolify budo_erfahrung
        if "Ja" in str(budo["War_schon_mal_im_Bunten_Dorf"][i]) or "ja" in str(budo["War_schon_mal_im_Bunten_Dorf"][i]):
            kid_budo_erfahrung = True
        elif "Nein" in str(budo["War_schon_mal_im_Bunten_Dorf"][i]) or "nein" in str(budo["War_schon_mal_im_Bunten_Dorf"][i]):
            kid_budo_erfahrung = False
        else:
            kid_budo_erfahrung = None

        kid = Kinder(
            kid_index=budo["Index"][i],
            kid_vorname=budo["Kind_Vorname"][i],
            kid_nachname=budo["Kind_Nachname"][i],
            zug_anreise=kid_anreise,
            zug_abreise=kid_abreise,
            top_jugendticket=kid_jugendticket,
            turnus_dauer=kid_dauer,
            geschwister=budo["Geschwister_am_Camp?"][i],
            zeltwunsch=budo["Zeltwunsch_mit_folgenden_anderen_Kindern"][i],
            schimmkenntnisse=budo["Schwimmkenntnisse"][i],
            haftpflichtversicherung=budo["Haftpflichtversicherung"][i],
            budo_erfahrung=kid_budo_erfahrung,
            anmerkung=budo["Anmerkungen"][i],
            # turnus = models.ForeignKey("Turnus", on_delete=models.SET_NULL, null=True)

            # # familie
            # anmelder_vorname = models.CharField(max_length=255)
            # anmelder_nachname = models.CharField(max_length=255)
            # anmelde_organisation = budo[""][i],
            # anmelder_email = models.CharField(max_length=255, null=True, default=None)
            # anmelder_mobil = budo[""][i],
            # hauptversichert_bei = budo[""][i],
            # # rechnung
            # rechnungsadresse = models.CharField(max_length=255)
            # rechnung_plz = models.IntegerField(null=True, default=None)
            # rechnung_ort = models.CharField(max_length=255)
            # rechnung_land = models.CharField(max_length=255)
            # notfall_kontakte = models.CharField(
            #     max_length=255, null=True)  # import from rawdata

            # # health

            # sex = models.CharField
            # sozialversicherungsnr = budo[""][i],
            # tetanusimpfung = budo[""][i],
            # zeckenimpfung = budo[""][i],
            # vegetarisch = budo[""][i],
            # special_food_description = budo[""][i],
            # drugs = budo[""][i],
            # illness = budo[""][i],
            # rezeptfreie_medikamente = budo[""][i],
            # rezept_medikamente = budo[""][i],
            # covid = budo[""][i],

            # # anwesenheit

            # anwesend = models.BooleanField(null=True, default=None)
            # late_anreise = models.DateField(null=True)
            # early_abreise_date = models.DateField(null=True)
            # early_abreise_abholer = budo[""][i],
            # early_abreise_reason = budo[""][i],
            # came_back = models.DateField(null=True)
        )
        kid.save()
