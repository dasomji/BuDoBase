from budo_database.settings import MEDIA_ROOT
from . import models
import pandas as pd
import os
from datetime import datetime, timedelta


def from_excel_ordinal(ordinal: float, _epoch0=datetime(1899, 12, 31)) -> datetime:
    if ordinal >= 60:
        ordinal -= 1  # Excel leap year bug, 1900 is not a leap year!
    return (_epoch0 + timedelta(days=ordinal)).replace(microsecond=0).strftime('%Y-%m-%d')


def process_excel():
    this_turnus = models.Turnus.objects.last()
    path = os.path.join(MEDIA_ROOT, str(this_turnus.uploadedFile))

    budo = pd.read_excel(
        open(path, "rb"), sheet_name="DataCleaner", header=1)
    budo_raw = pd.read_excel(
        open(path, "rb"), sheet_name="RawData", header=0)
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

        # cleaning Notfallkontake from RawData
        cleaned_notfall = str(budo_raw["Notfall Kontakte"][i]).replace(
            "<p>", "").replace("</p>", "")

        birthday = from_excel_ordinal(float(budo["Kind_Geburtsdatum"][i]))

        kid = models.Kinder(
            kid_index=budo["Index"][i],
            kid_vorname=budo["Kind_Vorname"][i],
            kid_nachname=budo["Kind_Nachname"][i],
            kid_alter=budo["Kind_Alter"][i],
            kid_birthday=birthday,
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
            anmerkung_buchung=budo["Anmerkungen_Buchung"][i],
            turnus=this_turnus,

            # familie
            anmelder_vorname=budo["Anmelder_Vorname"][i],
            anmelder_nachname=budo["Anmelder_Nachname"][i],
            anmelde_organisation=budo["Organisation"][i],
            anmelder_email=budo["Anmelder_Email"][i],
            anmelder_mobil=budo["Anmelder_mobil"][i],
            hauptversichert_bei=budo[
                "Hauptversicherten_Person,_bei_der_das_Kind_mitversichert_ist_(Sozialversicherung)"][i],
            notfall_kontakte=cleaned_notfall,
            # rechnung
            rechnungsadresse=budo["Rechnungsadresse"][i],
            rechnung_plz=int(budo["Rechnung_PLZ"][i]),
            rechnung_ort=budo["Rechnung_Ort"][i],
            rechnung_land=budo["Rechnung_Land"][i],


            # health

            sex=budo["Kind_Geschlecht"][i],
            sozialversicherungsnr=budo["Sozialversicherung_Kind"][i],
            tetanusimpfung=budo["Tetanusimpfung"][i],
            zeckenimpfung=budo["Zeckenimpfung"][i],
            vegetarisch=budo["Vegetarisch"][i],
            special_food_description=budo["Ernährungsvorgaben"][i],
            drugs=budo["Muss_ihr_Kind_Medikamente_einnehmen?"][i],
            illness=budo["Hat_Ihr_Kind_eine_Krankheit,_körperliche_Einschränkungen_oder_besondere_Bedürfnisse?"][i],
            rezeptfreie_medikamente=budo["Stimmen_Sie_der_Verabreichung_von_NICHT-rezeptpflichtigen_Medikamenten_zu,_wie_zum_Beispiel_Salbe_bei_Insektenstich?"][i],
            rezept_medikamente=budo["Stimmen_Sie_der_Verabreichung_von_rezeptpflichtigen_Medikamenten_zu,_welche_Ihrem_Kind_von_einem_Arzt_verordnet_wurden?"][i],
            swimmer=budo["Schwimmkenntnisse"][i],
            covid=budo["Covid"][i],

            # Anwesenheit & Schwerpunkte werden nicht aus dem Excel-File extrahiert sondern durch Eingaben ergänzt

        )
        kid.save()


def postprocessing():
    age_ordered = models.Kinder.objects.all().order_by('kid_alter')
    length = len(models.Kinder.objects.all())

    for i, kid in enumerate(age_ordered):
        x = age_ordered[i]
        if i < length/4:
            x.budo_family = "smallie"
        elif i < length/2:
            x.budo_family = "medi"
        elif i < (length*3/4):
            x.budo_family = "largie"
        else:
            x.budo_family = "x-largie"
        x.save()
