from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader
from budo_database.settings import MEDIA_ROOT
from .excelProcessor import process
from . import models
import pandas as pd
import os

# Create your views here.


def budo_app(request):
    template = loader.get_template('myfirst.html')
    return HttpResponse(template.render())


def uploadFile(request):
    if request.method == "POST":
        # Fetching the form data
        turnus_number = request.POST["turnus_nr"]
        turnus_jahr = request.POST["turnus_year"]
        uploadedFile = request.FILES["uploadedFile"]

        # Saving the information in the database
        turnus = models.Turnus(
            turnus_nr=int(turnus_number),
            turnus_year=int(turnus_jahr),
            uploadedFile=uploadedFile
        )
        turnus.save()

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

            kid = models.Kinder(
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
                covid=budo["Covid"][i],

                # Anwesenheit & Schwerpunkte werden nicht aus dem Excel-File extrahiert sondern durch Eingaben ergänzt

            )
            kid.save()

    documents = models.Turnus.objects.all()

    return render(request, "upload-file.html", context={
        "files": documents
    })
