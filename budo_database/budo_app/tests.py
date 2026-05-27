from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Turnus, Kinder
from .excelProcessor import process_excel, validate_workbook_columns
from unittest.mock import patch
from django.contrib.auth.models import User
import os
import json
import pandas as pd
from datetime import date


def make_kid(turnus, kid_index="T1-1", first_name="Test", last_name="Kind"):
    return Kinder.objects.create(
        kid_index=kid_index,
        kid_vorname=first_name,
        kid_nachname=last_name,
        kid_birthday=date(2014, 1, 1),
        turnus=turnus,
        anmelder_vorname="Parent",
        anmelder_nachname="User",
        rechnungsadresse="Example Street 1",
        rechnung_ort="Wien",
        rechnung_land="AT",
    )


def sample_excel_frames():
    budo = pd.DataFrame([{
        "Index": "T1-1",
        "AnreiseText": "Betreute Anreise, Top Jugendticket ist vorhanden",
        "AbreiseText": "Betreute Abreise",
        "Turnusdauer": "ganz",
        "War_schon_mal_im_Bunten_Dorf": "Ja",
        "Notfall_Kontakte": "Mama",
        "Kind_Geburtsdatum": "01.01.2014",
        "Kind_Vorname": "Test",
        "Kind_Nachname": "Kind",
        "Geschwister_am_Camp?": "nein",
        "Zeltwunsch_mit_folgenden_anderen_Kindern": "nein",
        "Schwimmkenntnisse": "ja",
        "Haftpflichtversicherung": "ja",
        "Anmerkungen": "",
        "Anmerkungen_Buchung": "",
        "Anmelder_Vorname": "Parent",
        "Anmelder_Nachname": "User",
        "Organisation": "",
        "Anmelder_Email": "parent@example.com",
        "Anmelder_mobil": "123",
        "Hauptversicherten_Person,_bei_der_das_Kind_mitversichert_ist_(Sozialversicherung)": "Parent",
        "Rechnungsadresse": "Example Street 1",
        "Rechnung_PLZ": 1010,
        "Rechnung_Ort": "Wien",
        "Rechnung_Land": "AT",
        "Kind_Geschlecht": "weiblich",
        "Sozialversicherung_Kind": "",
        "Tetanusimpfung": "",
        "Zeckenimpfung": "",
        "Vegetarisch": "nein",
        "Ernährungsvorgaben": "nein",
        "Muss_ihr_Kind_Medikamente_einnehmen?": "nein",
        "Hat_Ihr_Kind_eine_Krankheit,_körperliche_Einschränkungen_oder_besondere_Bedürfnisse?": "nein",
        "Stimmen_Sie_der_Verabreichung_von_NICHT-rezeptpflichtigen_Medikamenten_zu,_wie_zum_Beispiel_Salbe_bei_Insektenstich?": "ja",
        "Stimmen_Sie_der_Verabreichung_von_rezeptpflichtigen_Medikamenten_zu,_welche_Ihrem_Kind_von_einem_Arzt_verordnet_wurden?": "ja",
    }])
    budo_raw = pd.DataFrame([{
        "Index": "T1-1",
        "Submitted": "",
        "Anmelder Email": "parent@example.com",
        "Notfall Kontakte": "Mama",
    }])
    return budo, budo_raw


class MutationSecurityTest(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.user = User.objects.create_user(
            username='secureuser',
            password='testpass123'
        )
        self.active_turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2024, 7, 1)
        )
        self.other_turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2024, 8, 1)
        )
        self.user.profil.turnus = self.active_turnus
        self.user.profil.save()
        self.active_kid = make_kid(self.active_turnus, "T1-1")
        self.other_kid = make_kid(self.other_turnus, "T2-1")

    def test_update_pfand_requires_login(self):
        client = Client()
        response = client.post(
            reverse('update_pfand'),
            data=json.dumps({'id': self.active_kid.id, 'action': 'increase'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 302)
        self.active_kid.refresh_from_db()
        self.assertEqual(self.active_kid.pfand, 0)

    def test_update_pfand_rejects_missing_csrf(self):
        self.client.login(username='secureuser', password='testpass123')

        response = self.client.post(
            reverse('update_pfand'),
            data=json.dumps({'id': self.active_kid.id, 'action': 'increase'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)
        self.active_kid.refresh_from_db()
        self.assertEqual(self.active_kid.pfand, 0)

    def test_update_pfand_rejects_cross_turnus_kid(self):
        self.client.login(username='secureuser', password='testpass123')
        csrf_token = 'a' * 32
        self.client.cookies['csrftoken'] = csrf_token

        response = self.client.post(
            reverse('update_pfand'),
            data=json.dumps({'id': self.other_kid.id, 'action': 'increase'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 404)
        self.other_kid.refresh_from_db()
        self.assertEqual(self.other_kid.pfand, 0)


class KinderModelTest(TestCase):
    def test_get_alter_returns_none_without_turnus(self):
        kid = make_kid(turnus=None)

        self.assertIsNone(kid.get_alter())

    def test_is_birthday_during_turnus_returns_false_without_birthday(self):
        turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2024, 7, 1)
        )
        kid = make_kid(turnus=turnus)
        kid.kid_birthday = None

        self.assertFalse(kid.is_birthday_during_turnus())

    def test_get_clean_anmerkung_buchung_uses_buchung_field(self):
        kid = make_kid(turnus=None)
        kid.anmerkung = "Visible team note"
        kid.anmerkung_buchung = "nein"

        self.assertEqual(kid.get_clean_anmerkung_buchung(), "")

    def test_get_clean_anmerkung_buchung_keeps_real_value(self):
        kid = make_kid(turnus=None)
        kid.anmerkung = "nein"
        kid.anmerkung_buchung = "Needs a lower bunk"

        self.assertEqual(
            kid.get_clean_anmerkung_buchung(), "Needs a lower bunk")


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

        self.test_file = SimpleUploadedFile(
            name='detail_test.xlsx',
            content=b'test-content',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    @patch('budo_app.excel_views.process_excel')
    def test_turnus_upload_and_process(self, process_excel_mock):
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
        process_excel_mock.assert_called_once_with(turnus)


class ExcelProcessingTransactionTest(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2024, 7, 1)
        )

        self.turnus.uploadedFile.name = 'detail_test.xlsx'
        self.turnus.save()

    @patch('budo_app.excelProcessor.get_uploaded_excel_path')
    @patch('budo_app.excelProcessor.read_workbook')
    def test_successful_processing_with_selected_turnus(self, mock_read_workbook, mock_path):
        mock_path.return_value = 'detail_test.xlsx'
        mock_read_workbook.return_value = sample_excel_frames()
        kids_before = Kinder.objects.count()

        process_excel(self.turnus)

        kids_after = Kinder.objects.count()
        self.assertGreater(kids_after, kids_before,
                           "Expected kids to be created from the Excel data")

        kids = Kinder.objects.filter(turnus=self.turnus)
        self.assertGreater(len(kids), 0, "No kids were created")
        first_kid = kids.first()
        self.assertIsNotNone(first_kid.kid_index)
        self.assertIsNotNone(first_kid.kid_vorname)
        self.assertIsNotNone(first_kid.kid_nachname)
        self.assertEqual(first_kid.turnus, self.turnus)

    @patch('budo_app.excelProcessor.get_uploaded_excel_path')
    @patch('budo_app.excelProcessor.read_workbook')
    @patch('budo_app.models.Kinder.save')
    def test_transaction_rollback_on_save_error(self, mock_save, mock_read_workbook, mock_path):
        mock_path.return_value = 'detail_test.xlsx'
        mock_read_workbook.return_value = sample_excel_frames()
        """Test that transaction is rolled back when kid.save() fails during processing"""
        # Configure mock to raise an exception on the first save call
        mock_save.side_effect = Exception("Database error during save")

        # Count kids before processing
        kids_before = Kinder.objects.count()

        # Process Excel and expect it to fail
        with self.assertRaises(Exception) as context:
            process_excel(self.turnus)

        # Verify the exception message contains our expected error
        self.assertIn("Database error during save", str(context.exception))

        # Verify that no kids were created due to transaction rollback
        kids_after = Kinder.objects.count()
        self.assertEqual(kids_before, kids_after,
                         "Transaction rollback failed - kids were created despite error")

    @patch('budo_app.excelProcessor.get_uploaded_excel_path')
    @patch('budo_app.excelProcessor.read_workbook')
    def test_transaction_rollback_on_excel_read_error(self, mock_read_workbook, mock_path):
        mock_path.return_value = 'detail_test.xlsx'
        """Test that transaction is rolled back when Excel reading fails"""
        # Configure mock to raise an exception when reading Excel
        mock_read_workbook.side_effect = Exception("Excel file is corrupted")

        # Count kids before processing
        kids_before = Kinder.objects.count()

        # Process Excel and expect it to fail
        with self.assertRaises(Exception) as context:
            process_excel(self.turnus)

        # Verify the exception message contains our expected error
        self.assertIn("Excel file is corrupted", str(context.exception))

        # Verify that no kids were created due to transaction rollback
        kids_after = Kinder.objects.count()
        self.assertEqual(kids_before, kids_after,
                         "Transaction rollback failed - kids were created despite error")

    @patch('budo_app.excelProcessor.get_uploaded_excel_path')
    @patch('budo_app.excelProcessor.read_workbook')
    @patch('budo_app.excelProcessor.from_excel_ordinal')
    def test_transaction_rollback_on_date_parsing_error(self, mock_date_parser, mock_read_workbook, mock_path):
        mock_path.return_value = 'detail_test.xlsx'
        budo, budo_raw = sample_excel_frames()
        budo.loc[0, "Kind_Geburtsdatum"] = 12345
        mock_read_workbook.return_value = (budo, budo_raw)
        """Test that transaction is rolled back when date parsing fails during processing"""
        # Configure mock to raise an exception during date parsing
        mock_date_parser.side_effect = Exception("Invalid date format")

        # Count kids before processing
        kids_before = Kinder.objects.count()

        # Process Excel and expect it to fail
        with self.assertRaises(Exception) as context:
            process_excel(self.turnus)

        # Verify the exception message contains our expected error
        self.assertIn("Invalid date format", str(context.exception))

        # Verify that no kids were created due to transaction rollback
        kids_after = Kinder.objects.count()
        self.assertEqual(kids_before, kids_after,
                         "Transaction rollback failed - kids were created despite error")

    def test_transaction_rollback_on_missing_file(self):
        """Test that transaction is rolled back when Excel file is missing"""
        # Set a non-existent file path
        self.turnus.uploadedFile.name = 'non_existent_file.xlsx'
        self.turnus.save()

        # Count kids before processing
        kids_before = Kinder.objects.count()

        # Process Excel and expect it to fail
        with self.assertRaises(Exception) as context:
            process_excel(self.turnus)

        # Verify the exception is about file not found
        self.assertIn("not found", str(context.exception))

        # Verify that no kids were created due to transaction rollback
        kids_after = Kinder.objects.count()
        self.assertEqual(kids_before, kids_after,
                         "Transaction rollback failed - kids were created despite error")

    @patch('budo_app.excelProcessor.get_uploaded_excel_path')
    @patch('budo_app.excelProcessor.read_workbook')
    @patch('budo_app.excelProcessor.assign_budo_families')
    def test_transaction_rollback_on_family_assignment_error(self, mock_assign, mock_read_workbook, mock_path):
        mock_path.return_value = 'detail_test.xlsx'
        mock_read_workbook.return_value = sample_excel_frames()
        mock_assign.side_effect = Exception("Family assignment failed")

        # Count kids before processing
        kids_before = Kinder.objects.count()

        # Process Excel and expect it to fail during family assignment
        with self.assertRaises(Exception) as context:
            process_excel(self.turnus)

        # Verify the exception is about family assignment
        self.assertIn("Family assignment failed", str(context.exception))

        # Verify that no kids were created due to transaction rollback
        kids_after = Kinder.objects.count()
        self.assertEqual(kids_before, kids_after,
                         "Transaction rollback failed - kids were created despite error")

    def test_missing_required_excel_column_reports_column_name(self):
        budo, _ = sample_excel_frames()
        budo = budo.drop(columns=["Kind_Vorname"])

        with self.assertRaises(ValueError) as context:
            validate_workbook_columns(budo)

        self.assertIn("Kind_Vorname", str(context.exception))

    @patch('budo_app.excelProcessor.get_uploaded_excel_path')
    @patch('budo_app.excelProcessor.read_workbook')
    def test_invalid_birthday_reports_expected_formats(self, mock_read_workbook, mock_path):
        mock_path.return_value = 'detail_test.xlsx'
        budo, budo_raw = sample_excel_frames()
        budo.loc[0, "Kind_Geburtsdatum"] = "not-a-date"
        mock_read_workbook.return_value = (budo, budo_raw)

        with self.assertRaises(ValueError) as context:
            process_excel(self.turnus)

        self.assertIn("Invalid birthday", str(context.exception))
        self.assertIn("DD.MM.YYYY", str(context.exception))
