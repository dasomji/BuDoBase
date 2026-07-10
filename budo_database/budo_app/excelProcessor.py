from budo_database.settings import MEDIA_ROOT
from . import models
import pandas as pd
import os
from datetime import datetime, timedelta
from django.db import transaction
import logging
import html
import re

logger = logging.getLogger(__name__)

REQUIRED_DATA_CLEANER_COLUMNS = (
    "Index",
    "AnreiseText",
    "AbreiseText",
    "Turnusdauer",
    "War_schon_mal_im_Bunten_Dorf",
    "Kind_Geburtsdatum",
    "Kind_Vorname",
    "Kind_Nachname",
    "Geschwister_am_Camp?",
    "Zeltwunsch_mit_folgenden_anderen_Kindern",
    "Schwimmkenntnisse",
    "Haftpflichtversicherung",
    "Anmerkungen",
    "Anmerkungen_Buchung",
    "Anmelder_Vorname",
    "Anmelder_Nachname",
    "Organisation",
    "Anmelder_Email",
    "Anmelder_mobil",
    "Hauptversicherten_Person,_bei_der_das_Kind_mitversichert_ist_(Sozialversicherung)",
    "Rechnungsadresse",
    "Rechnung_PLZ",
    "Rechnung_Ort",
    "Rechnung_Land",
    "Kind_Geschlecht",
    "Sozialversicherung_Kind",
    "Tetanusimpfung",
    "Zeckenimpfung",
    "Vegetarisch",
    "Ernährungsvorgaben",
    "Muss_ihr_Kind_Medikamente_einnehmen?",
    "Hat_Ihr_Kind_eine_Krankheit,_körperliche_Einschränkungen_oder_besondere_Bedürfnisse?",
    "Stimmen_Sie_der_Verabreichung_von_NICHT-rezeptpflichtigen_Medikamenten_zu,_wie_zum_Beispiel_Salbe_bei_Insektenstich?",
    "Stimmen_Sie_der_Verabreichung_von_rezeptpflichtigen_Medikamenten_zu,_welche_Ihrem_Kind_von_einem_Arzt_verordnet_wurden?",
)


def decode_html_entities(text):
    """
    Decode HTML entities in text fields.
    Returns empty string if text is None or NaN.
    """
    if text is None or pd.isna(text):
        return ""
    text_str = str(text)
    if text_str.lower().strip() in ("nan", "none", ""):
        return ""
    return html.unescape(text_str)


def from_excel_ordinal(ordinal: float, _epoch0=datetime(1899, 12, 31)) -> datetime:
    if ordinal >= 60:
        ordinal -= 1  # Excel leap year bug, 1900 is not a leap year!
    return (_epoch0 + timedelta(days=ordinal)).replace(microsecond=0)


def get_turnus_for_import(turnus=None):
    this_turnus = turnus or models.Turnus.objects.last()
    if not this_turnus or not this_turnus.uploadedFile:
        raise ValueError("No turnus found or no uploaded file")
    return this_turnus


def get_uploaded_excel_path(turnus):
    path = os.path.join(MEDIA_ROOT, str(turnus.uploadedFile))
    if not os.path.exists(path):
        raise FileNotFoundError(f"Excel file not found at path: {path}")
    return path


def validate_workbook_columns(budo):
    missing_columns = [
        column for column in REQUIRED_DATA_CLEANER_COLUMNS
        if column not in budo.columns
    ]
    if missing_columns:
        raise ValueError(
            "DataCleaner sheet is missing required columns: "
            + ", ".join(missing_columns)
        )


def read_workbook(path):
    try:
        with open(path, "rb") as excel_file:
            budo = pd.read_excel(
                excel_file, sheet_name="DataCleaner", header=1)
            excel_file.seek(0)
            budo_raw = pd.read_excel(
                excel_file, sheet_name="RawData", header=0)
    except Exception as e:
        raise ValueError(f"Error reading Excel file: {str(e)}")

    if len(budo) == 0:
        raise ValueError("No data found in Excel file")

    validate_workbook_columns(budo)

    return budo, budo_raw


def should_skip_manual_override(budo, budo_raw, row_index):
    try:
        current_index = budo["Index"][row_index]
        if "Index" in budo_raw.columns:
            matching_row = budo_raw[budo_raw["Index"] == current_index]
            if not matching_row.empty:
                return (
                    matching_row["Submitted"].iloc[0] == "MANUAL OVERRIDE" or
                    matching_row["Anmelder Email"].iloc[0] == "MANUAL OVERRIDE"
                )

        return (
            budo_raw["Submitted"][row_index] == "MANUAL OVERRIDE" or
            budo_raw["Anmelder Email"][row_index] == "MANUAL OVERRIDE"
        )
    except (KeyError, IndexError):
        return False


def get_notfall_kontakte(budo, budo_raw, row_index):
    try:
        return decode_html_entities(str(budo["Notfall_Kontakte"][row_index]))
    except KeyError:
        pass

    try:
        current_index = budo["Index"][row_index]
        if "Index" in budo_raw.columns:
            matching_row = budo_raw[budo_raw["Index"] == current_index]
            if matching_row.empty:
                return ""
            raw_notfall = matching_row["Notfall Kontakte"].iloc[0]
        else:
            raw_notfall = budo_raw["Notfall Kontakte"][row_index]
    except (KeyError, IndexError):
        return ""

    return decode_html_entities(str(raw_notfall).replace("<p>", "").replace("</p>", ""))


def parse_birthday(value):
    if value is None or pd.isna(value):
        raise ValueError("Missing birthday")

    if isinstance(value, pd.Timestamp):
        return value.date()

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return from_excel_ordinal(float(value)).date()

    value_text = str(value).strip()
    for date_format in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value_text, date_format).date()
        except ValueError:
            pass

    try:
        return from_excel_ordinal(float(value_text)).date()
    except (OverflowError, ValueError):
        pass

    raise ValueError(
        f"Invalid birthday '{value_text}'. Expected Excel date, ordinal, or DD.MM.YYYY"
    )


def parse_budo_erfahrung(value):
    value = str(value)
    if "Ja" in value or "ja" in value:
        return True
    if "Nein" in value or "nein" in value:
        return False
    return None


def parse_postal_code(value):
    if value is None or pd.isna(value):
        return None

    value_text = str(value).strip()

    try:
        numeric_value = float(value_text)
        if numeric_value.is_integer():
            return int(numeric_value)
    except ValueError:
        pass

    postal_code_with_locality = re.fullmatch(r"(\d+)\s+\D.*", value_text)
    if postal_code_with_locality:
        return int(postal_code_with_locality.group(1))

    raise ValueError(f"Invalid postal code '{value_text}'")


def assign_budo_families(kids, turnus):
    kids_with_age = []
    for kid in kids:
        try:
            delta = turnus.turnus_beginn - kid.kid_birthday
            age = round(delta.days / 365.25, 2) if kid.kid_birthday else None
            kids_with_age.append((kid, age))
        except Exception as e:
            logger.error(
                f"Error calculating age for kid {kid.kid_index}: {str(e)}")
            raise ValueError(
                f"Error calculating age for kid {kid.kid_index}: {str(e)}")

    logger.info(f"Calculated ages for {len(kids_with_age)} kids")
    kids_with_age.sort(
        key=lambda x: x[1] if x[1] is not None else float('inf'))

    length = len(kids_with_age)
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


@transaction.atomic
def process_excel(turnus=None):
    """
    Process Excel file and create Kinder records in a transactional manner.
    If any error occurs, all changes will be rolled back.
    """
    logger.info("Starting Excel processing")

    try:
        this_turnus = get_turnus_for_import(turnus)
        path = get_uploaded_excel_path(this_turnus)

        logger.info(f"Processing Excel file: {path}")

        budo, budo_raw = read_workbook(path)

        logger.info(f"Found {len(budo)} rows to process")

        processed_kids = []

        for i in range(0, len(budo)):
            try:
                if should_skip_manual_override(budo, budo_raw, i):
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

                kid_budo_erfahrung = parse_budo_erfahrung(
                    budo["War_schon_mal_im_Bunten_Dorf"][i])
                cleaned_notfall = get_notfall_kontakte(budo, budo_raw, i)
                birthday = parse_birthday(budo["Kind_Geburtsdatum"][i])

                # Create Kinder object
                kid = models.Kinder(
                    kid_index=budo["Index"][i],
                    kid_vorname=decode_html_entities(budo["Kind_Vorname"][i]),
                    kid_nachname=decode_html_entities(
                        budo["Kind_Nachname"][i]),
                    kid_birthday=birthday,
                    zug_anreise=kid_anreise,
                    zug_abreise=kid_abreise,
                    top_jugendticket=kid_jugendticket,
                    turnus_dauer=kid_dauer,
                    geschwister=decode_html_entities(
                        budo["Geschwister_am_Camp?"][i]),
                    zeltwunsch=decode_html_entities(
                        budo["Zeltwunsch_mit_folgenden_anderen_Kindern"][i]),
                    schimmkenntnisse=decode_html_entities(
                        budo["Schwimmkenntnisse"][i]),
                    haftpflichtversicherung=decode_html_entities(
                        budo["Haftpflichtversicherung"][i]),
                    budo_erfahrung=kid_budo_erfahrung,
                    anmerkung=decode_html_entities(budo["Anmerkungen"][i]),
                    anmerkung_buchung=decode_html_entities(
                        budo["Anmerkungen_Buchung"][i]),
                    turnus=this_turnus,

                    # familie
                    anmelder_vorname=decode_html_entities(
                        budo["Anmelder_Vorname"][i]),
                    anmelder_nachname=decode_html_entities(
                        budo["Anmelder_Nachname"][i]),
                    anmelde_organisation=decode_html_entities(
                        budo["Organisation"][i]),
                    anmelder_email=decode_html_entities(
                        budo["Anmelder_Email"][i]),
                    anmelder_mobil=decode_html_entities(
                        budo["Anmelder_mobil"][i]),
                    hauptversichert_bei=decode_html_entities(budo[
                        "Hauptversicherten_Person,_bei_der_das_Kind_mitversichert_ist_(Sozialversicherung)"][i]),
                    notfall_kontakte=cleaned_notfall,

                    # rechnung
                    rechnungsadresse=decode_html_entities(
                        budo["Rechnungsadresse"][i]),
                    rechnung_plz=parse_postal_code(budo["Rechnung_PLZ"][i]),
                    rechnung_ort=decode_html_entities(budo["Rechnung_Ort"][i]),
                    rechnung_land=decode_html_entities(
                        budo["Rechnung_Land"][i]),

                    # health
                    sex=decode_html_entities(budo["Kind_Geschlecht"][i]),
                    sozialversicherungsnr=decode_html_entities(
                        budo["Sozialversicherung_Kind"][i]),
                    tetanusimpfung=decode_html_entities(
                        budo["Tetanusimpfung"][i]),
                    zeckenimpfung=decode_html_entities(
                        budo["Zeckenimpfung"][i]),
                    vegetarisch=decode_html_entities(budo["Vegetarisch"][i]),
                    special_food_description=decode_html_entities(
                        budo["Ernährungsvorgaben"][i]),
                    drugs=decode_html_entities(
                        budo["Muss_ihr_Kind_Medikamente_einnehmen?"][i]),
                    illness=decode_html_entities(
                        budo["Hat_Ihr_Kind_eine_Krankheit,_körperliche_Einschränkungen_oder_besondere_Bedürfnisse?"][i]),
                    rezeptfreie_medikamente=decode_html_entities(
                        budo["Stimmen_Sie_der_Verabreichung_von_NICHT-rezeptpflichtigen_Medikamenten_zu,_wie_zum_Beispiel_Salbe_bei_Insektenstich?"][i]),
                    rezept_medikamente=decode_html_entities(
                        budo["Stimmen_Sie_der_Verabreichung_von_rezeptpflichtigen_Medikamenten_zu,_welche_Ihrem_Kind_von_einem_Arzt_verordnet_wurden?"][i]),
                    swimmer=decode_html_entities(budo["Schwimmkenntnisse"][i]),
                )

                kid.save()
                processed_kids.append(kid)

            except Exception as e:
                logger.error(f"Error processing row {i}: {str(e)}")
                raise ValueError(f"Error processing row {i+1}: {str(e)}")

        logger.info(f"Successfully processed {len(processed_kids)} kids")

        assign_budo_families(processed_kids, this_turnus)

        logger.info("Excel processing completed successfully")

    except Exception as e:
        logger.error(f"Excel processing failed: {str(e)}")
        raise  # Re-raise the exception to trigger transaction rollback
