from budo_database.settings import MEDIA_ROOT
from . import models
import pandas as pd
import os
from datetime import datetime, timedelta
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


def from_excel_ordinal(ordinal: float, _epoch0=datetime(1899, 12, 31)) -> datetime:
    if ordinal >= 60:
        ordinal -= 1  # Excel leap year bug, 1900 is not a leap year!
    return (_epoch0 + timedelta(days=ordinal)).replace(microsecond=0).strftime('%Y-%m-%d')


@transaction.atomic
def process_excel():
    """
    Process Excel file and create Kinder records in a transactional manner.
    If any error occurs, all changes will be rolled back.
    """
    logger.info("Starting Excel processing")

    try:
        this_turnus = models.Turnus.objects.last()
        if not this_turnus or not this_turnus.uploadedFile:
            raise ValueError("No turnus found or no uploaded file")

        path = os.path.join(MEDIA_ROOT, str(this_turnus.uploadedFile))

        if not os.path.exists(path):
            raise FileNotFoundError(f"Excel file not found at path: {path}")

        logger.info(f"Processing Excel file: {path}")

        # Read Excel sheets
        try:
            budo = pd.read_excel(
                open(path, "rb"), sheet_name="DataCleaner", header=1)
            budo_raw = pd.read_excel(
                open(path, "rb"), sheet_name="RawData", header=0)
        except Exception as e:
            raise ValueError(f"Error reading Excel file: {str(e)}")

        if len(budo) == 0:
            raise ValueError("No data found in Excel file")

        logger.info(f"Found {len(budo)} rows to process")

        processed_kids = []

        for i in range(0, len(budo)):
            try:
                # Skip entries with "MANUAL OVERRIDE"
                if (budo_raw["Submitted"][i] == "MANUAL OVERRIDE" or
                        budo_raw["Anmelder Email"][i] == "MANUAL OVERRIDE"):
                    continue

                # turn Anreise string into boolean, True = Zuganreise
                if "Betreute Anreise" in str(budo["AnreiseText"][i]):
                    kid_anreise = True
                else:
                    kid_anreise = False

                # turn Abreise string into boolean, True = Zugabreise
                if "Betreute Abreise" in str(budo["AbreiseText"][i]):
                    kid_abreise = True
                else:
                    kid_abreise = False

                # extract from Abreise and Anreise if kid has Top Jugendticket
                if (", Top Jugendticket ist vorhanden" in str(budo["AnreiseText"][i]) or
                        ", Top Jugendticket ist vorhanden" in str(budo["AbreiseText"][i])):
                    kid_jugendticket = True
                else:
                    kid_jugendticket = False

                # extract from Turnusdauer if kid stays one or two weeks
                if "ganz" in str(budo["Turnusdauer"][i]):
                    kid_dauer = 2
                else:
                    kid_dauer = 1

                # boolify budo_erfahrung
                budo_erfahrung_str = str(
                    budo["War_schon_mal_im_Bunten_Dorf"][i])
                if "Ja" in budo_erfahrung_str or "ja" in budo_erfahrung_str:
                    kid_budo_erfahrung = True
                elif "Nein" in budo_erfahrung_str or "nein" in budo_erfahrung_str:
                    kid_budo_erfahrung = False
                else:
                    kid_budo_erfahrung = None

                # cleaning Notfallkontake from RawData
                cleaned_notfall = str(budo_raw["Notfall Kontakte"][i]).replace(
                    "<p>", "").replace("</p>", "")

                # Handle birthday parsing
                birthday_value = budo["Kind_Geburtsdatum"][i]

                if isinstance(birthday_value, pd.Timestamp):
                    birthday_value = birthday_value.toordinal() + 366  # Convert to Excel ordinal
                    birthday = from_excel_ordinal(float(birthday_value))
                else:
                    try:
                        # Try to parse as a float (Excel ordinal)
                        birthday = from_excel_ordinal(float(birthday_value))
                    except ValueError:
                        # If parsing as float fails, assume it's a date string in dd.mm.yyyy format
                        birthday = datetime.strptime(
                            birthday_value, "%d.%m.%Y").strftime('%Y-%m-%d')

                # Create Kinder object
                kid = models.Kinder(
                    kid_index=budo["Index"][i],
                    kid_vorname=budo["Kind_Vorname"][i],
                    kid_nachname=budo["Kind_Nachname"][i],
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
                )

                kid.save()
                processed_kids.append(kid)

            except Exception as e:
                logger.error(f"Error processing row {i}: {str(e)}")
                raise ValueError(f"Error processing row {i+1}: {str(e)}")

        logger.info(f"Successfully processed {len(processed_kids)} kids")

        # Integrate put_kids_into_families logic here
        today = this_turnus.turnus_beginn

        # Calculate age for each kid and store it in a list of tuples (kid, age)
        kids_with_age = []
        for kid in processed_kids:
            try:
                delta = today - \
                    datetime.strptime(kid.kid_birthday, '%Y-%m-%d').date()
                age = round(delta.days / 365.25,
                            2) if kid.kid_birthday else None
                kids_with_age.append((kid, age))
            except Exception as e:
                logger.error(
                    f"Error calculating age for kid {kid.kid_index}: {str(e)}")
                raise ValueError(
                    f"Error calculating age for kid {kid.kid_index}: {str(e)}")

        logger.info(f"Calculated ages for {len(kids_with_age)} kids")

        # Sort the list of tuples by age
        kids_with_age.sort(
            key=lambda x: x[1] if x[1] is not None else float('inf'))

        length = len(kids_with_age)

        # Assign budo families
        for i, (kid, age) in enumerate(kids_with_age):
            try:
                if i < length / 4:
                    kid.budo_family = "S"
                elif i < length / 2:
                    kid.budo_family = "M"
                elif i < (length * 3 / 4):
                    kid.budo_family = "L"
                else:
                    kid.budo_family = "XL"
                kid.save()
            except Exception as e:
                logger.error(
                    f"Error assigning budo family for kid {kid.kid_index}: {str(e)}")
                raise ValueError(
                    f"Error assigning budo family for kid {kid.kid_index}: {str(e)}")

        logger.info("Excel processing completed successfully")

    except Exception as e:
        logger.error(f"Excel processing failed: {str(e)}")
        raise  # Re-raise the exception to trigger transaction rollback
