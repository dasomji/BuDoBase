import pandas as pd
from openpyxl import load_workbook
from . import models


def update_excel_file(file_path, turnus):
    print(
        f"Starting update_excel_file with file_path: {file_path} and turnus: {turnus}")

    # Create a new DataFrame with the required columns
    columns = ['Index', 'Vorname', 'Nachname', 'Anwesend 1. Woche',
               'Anwesend 2. Woche', 'verspätete Anreise', 'vorzeitige Abreise',
               'Zuganreise', 'Zugabreise', 'Abreisenotiz']  # Added 'Zuganreise', 'Zugabreise', and 'Abreisenotiz'
    df = pd.DataFrame(columns=columns)

    # List to hold data for each kid
    data_list = []

    # Populate the DataFrame with data from the Kinder model
    for kid in models.Kinder.objects.filter(turnus=turnus):
        data = {
            'Index': kid.kid_index,
            'Vorname': kid.kid_vorname,
            'Nachname': kid.kid_nachname,
            'Anwesend 1. Woche': 'ja' if kid.check_in_date and kid.turnus_dauer in [1, 2] else '',
            'Anwesend 2. Woche': 'ja' if kid.check_in_date and kid.turnus_dauer == 2 else '',
            'verspätete Anreise': kid.check_in_date.strftime('%Y-%m-%d') if kid.check_in_date and kid.check_in_date.strftime('%Y-%m-%d') != turnus.get_turnus_beginn_formatiert() else '',
            'vorzeitige Abreise': kid.early_abreise_date.strftime('%Y-%m-%d') if kid.early_abreise_date and kid.early_abreise_date.strftime('%Y-%m-%d') != turnus.get_turnus_ende().strftime('%Y-%m-%d') else '',
            'Zuganreise': 'ja' if kid.zug_anreise else '',
            'Zugabreise': 'ja' if kid.zug_abreise else '',
            'Abreisenotiz': kid.notiz_abreise  # Added 'Abreisenotiz'
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
    print("update_excel_file completed")
