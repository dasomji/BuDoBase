from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Turnus, Kinder
from .excelProcessor import process_excel
from django.db import transaction
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
import os
import tempfile
import pandas as pd
from datetime import date


class TurnusUploadTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('uploadFile')

        # Create a test user and log in
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')

        # Use the real test file provided
        self.test_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'test_files', 'detail_test.xlsx')

        self.test_file = SimpleUploadedFile(
            name='detail_test.xlsx',
            content=open(self.test_file_path, 'rb').read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def test_turnus_upload_and_process(self):
        # Provide complete form data
        form_data = {
            'turnus_nr': 1,
            'turnus_beginn': '2024-07-01',
            'uploadedFile': self.test_file
        }
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Turnus.objects.exists())
        turnus = Turnus.objects.last()
        self.assertIsNotNone(turnus.uploadedFile)
        self.assertTrue(os.path.exists(turnus.uploadedFile.path))

        # Verify that kids were created from the real Excel file
        kids_count = Kinder.objects.count()
        self.assertGreater(
            kids_count, 0, "Expected kids to be created from the Excel file")


class ExcelProcessingTransactionTest(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2024, 7, 1)
        )

        # Path to the real test file
        self.real_test_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'test_files', 'detail_test.xlsx')

    def test_transaction_rollback_on_error(self):
        """Test that transaction is rolled back when Excel processing fails"""
        # Create a mock Excel file that will cause an error during processing
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            # Create a simple Excel file with invalid data
            df = pd.DataFrame({
                'Index': ['T1-1', 'T1-2'],
                'Kind_Vorname': ['Test', 'Test2'],
                'Kind_Nachname': ['Kid', 'Kid2'],
                # Invalid date will cause error
                'Kind_Geburtsdatum': ['invalid_date', '2010-01-01'],
                'AnreiseText': ['Normal', 'Normal'],
                'AbreiseText': ['Normal', 'Normal'],
                'Turnusdauer': ['ganz', 'ganz'],
                'War_schon_mal_im_Bunten_Dorf': ['Nein', 'Nein'],
                'Geschwister_am_Camp?': ['', ''],
                'Zeltwunsch_mit_folgenden_anderen_Kindern': ['', ''],
                'Schwimmkenntnisse': ['Ja', 'Ja'],
                'Haftpflichtversicherung': ['Ja', 'Ja'],
                'Anmerkungen': ['', ''],
                'Anmerkungen_Buchung': ['', ''],
                'Anmelder_Vorname': ['Parent', 'Parent2'],
                'Anmelder_Nachname': ['One', 'Two'],
                'Organisation': ['', ''],
                'Anmelder_Email': ['parent@test.com', 'parent2@test.com'],
                'Anmelder_mobil': ['123456789', '987654321'],
                'Hauptversicherten_Person,_bei_der_das_Kind_mitversichert_ist_(Sozialversicherung)': ['Parent One', 'Parent Two'],
                'Rechnungsadresse': ['Test Address', 'Test Address 2'],
                'Rechnung_PLZ': [1010, 1020],
                'Rechnung_Ort': ['Vienna', 'Vienna'],
                'Rechnung_Land': ['Austria', 'Austria'],
                'Kind_Geschlecht': ['m', 'f'],
                'Sozialversicherung_Kind': ['123', '456'],
                'Tetanusimpfung': ['Ja', 'Ja'],
                'Zeckenimpfung': ['Ja', 'Ja'],
                'Vegetarisch': ['Nein', 'Nein'],
                'Ernährungsvorgaben': ['', ''],
                'Muss_ihr_Kind_Medikamente_einnehmen?': ['Nein', 'Nein'],
                'Hat_Ihr_Kind_eine_Krankheit,_körperliche_Einschränkungen_oder_besondere_Bedürfnisse?': ['Nein', 'Nein'],
                'Stimmen_Sie_der_Verabreichung_von_NICHT-rezeptpflichtigen_Medikamenten_zu,_wie_zum_Beispiel_Salbe_bei_Insektenstich?': ['Ja', 'Ja'],
                'Stimmen_Sie_der_Verabreichung_von_rezeptpflichtigen_Medikamenten_zu,_welche_Ihrem_Kind_von_einem_Arzt_verordnet_wurden?': ['Ja', 'Ja'],
            })

            # Create raw data sheet
            df_raw = pd.DataFrame({
                'Submitted': ['2024-01-01', '2024-01-02'],
                'Anmelder Email': ['parent@test.com', 'parent2@test.com'],
                'Notfall Kontakte': ['Emergency Contact 1', 'Emergency Contact 2']
            })

            with pd.ExcelWriter(tmp_file.name, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='DataCleaner',
                            index=False, startrow=1)
                df_raw.to_excel(writer, sheet_name='RawData', index=False)

            # Set the file path for the turnus
            self.turnus.uploadedFile.name = tmp_file.name
            self.turnus.save()

            # Count kids before processing
            kids_before = Kinder.objects.count()

            # Process Excel and expect it to fail
            with self.assertRaises(Exception):
                process_excel()

            # Verify that no kids were created due to transaction rollback
            kids_after = Kinder.objects.count()
            self.assertEqual(kids_before, kids_after,
                             "Transaction rollback failed - kids were created despite error")

            # Clean up
            os.unlink(tmp_file.name)

    def test_successful_processing_commits_transaction(self):
        """Test that successful Excel processing commits all data"""
        # Create a valid Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            df = pd.DataFrame({
                'Index': ['T1-1'],
                'Kind_Vorname': ['Test'],
                'Kind_Nachname': ['Kid'],
                'Kind_Geburtsdatum': ['01.01.2010'],  # Valid date format
                'AnreiseText': ['Normal'],
                'AbreiseText': ['Normal'],
                'Turnusdauer': ['ganz'],
                'War_schon_mal_im_Bunten_Dorf': ['Nein'],
                'Geschwister_am_Camp?': [''],
                'Zeltwunsch_mit_folgenden_anderen_Kindern': [''],
                'Schwimmkenntnisse': ['Ja'],
                'Haftpflichtversicherung': ['Ja'],
                'Anmerkungen': [''],
                'Anmerkungen_Buchung': [''],
                'Anmelder_Vorname': ['Parent'],
                'Anmelder_Nachname': ['One'],
                'Organisation': [''],
                'Anmelder_Email': ['parent@test.com'],
                'Anmelder_mobil': ['123456789'],
                'Hauptversicherten_Person,_bei_der_das_Kind_mitversichert_ist_(Sozialversicherung)': ['Parent One'],
                'Rechnungsadresse': ['Test Address'],
                'Rechnung_PLZ': [1010],
                'Rechnung_Ort': ['Vienna'],
                'Rechnung_Land': ['Austria'],
                'Kind_Geschlecht': ['m'],
                'Sozialversicherung_Kind': ['123'],
                'Tetanusimpfung': ['Ja'],
                'Zeckenimpfung': ['Ja'],
                'Vegetarisch': ['Nein'],
                'Ernährungsvorgaben': [''],
                'Muss_ihr_Kind_Medikamente_einnehmen?': ['Nein'],
                'Hat_Ihr_Kind_eine_Krankheit,_körperliche_Einschränkungen_oder_besondere_Bedürfnisse?': ['Nein'],
                'Stimmen_Sie_der_Verabreichung_von_NICHT-rezeptpflichtigen_Medikamenten_zu,_wie_zum_Beispiel_Salbe_bei_Insektenstich?': ['Ja'],
                'Stimmen_Sie_der_Verabreichung_von_rezeptpflichtigen_Medikamenten_zu,_welche_Ihrem_Kind_von_einem_Arzt_verordnet_wurden?': ['Ja'],
            })

            df_raw = pd.DataFrame({
                'Submitted': ['2024-01-01'],
                'Anmelder Email': ['parent@test.com'],
                'Notfall Kontakte': ['Emergency Contact 1']
            })

            with pd.ExcelWriter(tmp_file.name, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='DataCleaner',
                            index=False, startrow=1)
                df_raw.to_excel(writer, sheet_name='RawData', index=False)

            # Set the file path for the turnus
            self.turnus.uploadedFile.name = tmp_file.name
            self.turnus.save()

            # Count kids before processing
            kids_before = Kinder.objects.count()

            # Process Excel successfully
            process_excel()

            # Verify that kids were created
            kids_after = Kinder.objects.count()
            self.assertEqual(kids_after, kids_before + 1,
                             "Expected 1 kid to be created")

            # Verify the kid was created with correct data
            kid = Kinder.objects.last()
            self.assertEqual(kid.kid_index, 'T1-1')
            self.assertEqual(kid.kid_vorname, 'Test')
            self.assertEqual(kid.kid_nachname, 'Kid')
            self.assertEqual(kid.turnus, self.turnus)

            # Clean up
            os.unlink(tmp_file.name)

    def test_real_excel_file_processing(self):
        """Test that the real Excel file processes successfully with transactions"""
        # Use the real test file
        self.turnus.uploadedFile.name = self.real_test_file_path
        self.turnus.save()

        # Count kids before processing
        kids_before = Kinder.objects.count()

        # Process the real Excel file
        try:
            process_excel()
            processing_successful = True
        except Exception as e:
            processing_successful = False
            error_message = str(e)

        # If processing was successful, verify kids were created
        if processing_successful:
            kids_after = Kinder.objects.count()
            self.assertGreater(kids_after, kids_before,
                               "Expected kids to be created from the real Excel file")
            print(
                f"Successfully processed {kids_after - kids_before} kids from the real Excel file")
        else:
            # If processing failed, verify no partial data was left
            kids_after = Kinder.objects.count()
            self.assertEqual(kids_before, kids_after,
                             f"Transaction rollback failed - partial data was left after error: {error_message}")
            print(
                f"Excel processing failed as expected with error: {error_message}")
            print("Transaction rollback worked correctly - no partial data left")
