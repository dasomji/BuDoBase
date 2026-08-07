import pandas as pd
from openpyxl import load_workbook
from . import models
from .excelProcessor import read_workbook

import os
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)


def _original_booking_values(turnus):
    if not turnus.uploadedFile:
        return {}

    try:
        with turnus.uploadedFile.open("rb") as excel_file:
            source, _ = read_workbook(excel_file)
    except (FileNotFoundError, OSError, ValueError):
        logger.warning(
            "Could not read original workbook for turnus %s",
            turnus.pk,
            exc_info=True,
        )
        return {}

    values = {}
    for _, row in source.iterrows():
        kid_index = str(row["Index"]).strip()
        values[kid_index] = {
            "zug_abreise": "Betreute Abreise" in str(row["AbreiseText"]),
            "turnus_dauer": 2 if "ganz" in str(row["Turnusdauer"]) else 1,
        }
    return values


def _planned_departure(kid, turnus):
    # Turnus starts on Saturday; children arrive Sunday and leave Friday.
    days_after_start = 6 if kid.turnus_dauer == 1 else 13
    return turnus.turnus_beginn + timedelta(days=days_after_start)


def update_excel_file(file_path, turnus):
    logger.info("Starting update_excel_file with file_path=%s turnus=%s",
                file_path, turnus)

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Create a new DataFrame with the required columns
    columns = ['Index', 'Vorname', 'Nachname', 'Alter', 'Taschengeld', 'Anwesend 1. Woche',
               'Anwesend 2. Woche', 'verspätete Anreise', 'vorzeitige Abreise',
               'Zuganreise', 'Zugabreise', 'Zugabreise geändert',
               'Aufenthalt geändert', 'Abreisenotiz', 'Check-Out-Notiz']
    df = pd.DataFrame(columns=columns)

    # List to hold data for each kid
    data_list = []

    original_values = _original_booking_values(turnus)

    # Populate the DataFrame with data from the Kinder model
    for kid in models.Kinder.objects.filter(turnus=turnus):
        original = original_values.get(str(kid.kid_index).strip())
        data = {
            'Index': kid.kid_index,
            'Vorname': kid.kid_vorname,
            'Nachname': kid.kid_nachname,
            'Alter': kid.get_alter(),
            'Taschengeld': kid.get_taschengeld_sum(),
            'Anwesend 1. Woche': 'ja' if kid.check_in_date and kid.turnus_dauer in [1, 2] else '',
            'Anwesend 2. Woche': 'ja' if kid.check_in_date and kid.turnus_dauer == 2 else '',
            'verspätete Anreise': kid.check_in_date.strftime('%Y-%m-%d') if kid.check_in_date and kid.check_in_date != turnus.turnus_beginn + timedelta(days=1) else '',
            'vorzeitige Abreise': kid.early_abreise_date.strftime('%Y-%m-%d') if kid.early_abreise_date and kid.early_abreise_date < _planned_departure(kid, turnus) else '',
            'Zuganreise': 'ja' if kid.zug_anreise else '',
            'Zugabreise': 'ja' if kid.zug_abreise else '',
            'Zugabreise geändert': ('ja' if kid.zug_abreise != original['zug_abreise'] else 'nein') if original else '',
            'Aufenthalt geändert': ('ja' if kid.turnus_dauer != original['turnus_dauer'] else 'nein') if original else '',
            'Abreisenotiz': kid.notiz_abreise,
            'Check-Out-Notiz': kid.checkout_notiz,
        }
        data_list.append(data)

    # Convert the list of data to a DataFrame
    df = pd.DataFrame(data_list, columns=columns)

    # Save the DataFrame to a new Excel file
    df.to_excel(file_path, index=False)

    # Auto-fit column widths
    workbook = load_workbook(file_path)
    worksheet = workbook.active

    for column in worksheet.columns:
        max_length = 0
        column_letter = column[0].column_letter  # Get the column name
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = (max_length + 2)
        worksheet.column_dimensions[column_letter].width = adjusted_width

    workbook.save(file_path)
    logger.info("update_excel_file completed")
