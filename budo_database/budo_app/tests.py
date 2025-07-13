from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Turnus, Kinder
from .excelProcessor import process_excel
from django.db import transaction
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
import os
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

        # Set the real file path for the turnus
        self.turnus.uploadedFile.name = self.real_test_file_path
        self.turnus.save()

    def test_successful_processing_with_real_file(self):
        """Test that the real Excel file processes successfully with transactions"""
        # Count kids before processing
        kids_before = Kinder.objects.count()

        # Process the real Excel file
        try:
            process_excel()
            processing_successful = True
            error_message = None
        except Exception as e:
            processing_successful = False
            error_message = str(e)

        # Verify processing was successful
        self.assertTrue(processing_successful,
                        f"Excel processing failed: {error_message}")

        # Verify kids were created
        kids_after = Kinder.objects.count()
        self.assertGreater(kids_after, kids_before,
                           "Expected kids to be created from the real Excel file")

        # Verify the kids have correct data structure
        kids = Kinder.objects.filter(turnus=self.turnus)
        self.assertGreater(len(kids), 0, "No kids were created")

        # Check that at least one kid has the expected fields
        first_kid = kids.first()
        self.assertIsNotNone(first_kid.kid_index)
        self.assertIsNotNone(first_kid.kid_vorname)
        self.assertIsNotNone(first_kid.kid_nachname)
        self.assertEqual(first_kid.turnus, self.turnus)

        print(
            f"Successfully processed {kids_after - kids_before} kids from the real Excel file")

    @patch('budo_app.models.Kinder.save')
    def test_transaction_rollback_on_save_error(self, mock_save):
        """Test that transaction is rolled back when kid.save() fails during processing"""
        # Configure mock to raise an exception on the first save call
        mock_save.side_effect = Exception("Database error during save")

        # Count kids before processing
        kids_before = Kinder.objects.count()

        # Process Excel and expect it to fail
        with self.assertRaises(Exception) as context:
            process_excel()

        # Verify the exception message contains our expected error
        self.assertIn("Database error during save", str(context.exception))

        # Verify that no kids were created due to transaction rollback
        kids_after = Kinder.objects.count()
        self.assertEqual(kids_before, kids_after,
                         "Transaction rollback failed - kids were created despite error")

        print("Transaction rollback test passed - no kids were created after save error")

    @patch('pandas.read_excel')
    def test_transaction_rollback_on_excel_read_error(self, mock_read_excel):
        """Test that transaction is rolled back when Excel reading fails"""
        # Configure mock to raise an exception when reading Excel
        mock_read_excel.side_effect = Exception("Excel file is corrupted")

        # Count kids before processing
        kids_before = Kinder.objects.count()

        # Process Excel and expect it to fail
        with self.assertRaises(Exception) as context:
            process_excel()

        # Verify the exception message contains our expected error
        self.assertIn("Excel file is corrupted", str(context.exception))

        # Verify that no kids were created due to transaction rollback
        kids_after = Kinder.objects.count()
        self.assertEqual(kids_before, kids_after,
                         "Transaction rollback failed - kids were created despite error")

        print(
            "Transaction rollback test passed - no kids were created after Excel read error")

    @patch('budo_app.excelProcessor.from_excel_ordinal')
    def test_transaction_rollback_on_date_parsing_error(self, mock_date_parser):
        """Test that transaction is rolled back when date parsing fails during processing"""
        # Configure mock to raise an exception during date parsing
        mock_date_parser.side_effect = Exception("Invalid date format")

        # Count kids before processing
        kids_before = Kinder.objects.count()

        # Process Excel and expect it to fail
        with self.assertRaises(Exception) as context:
            process_excel()

        # Verify the exception message contains our expected error
        self.assertIn("Invalid date format", str(context.exception))

        # Verify that no kids were created due to transaction rollback
        kids_after = Kinder.objects.count()
        self.assertEqual(kids_before, kids_after,
                         "Transaction rollback failed - kids were created despite error")

        print("Transaction rollback test passed - no kids were created after date parsing error")

    def test_transaction_rollback_on_missing_file(self):
        """Test that transaction is rolled back when Excel file is missing"""
        # Set a non-existent file path
        self.turnus.uploadedFile.name = 'non_existent_file.xlsx'
        self.turnus.save()

        # Count kids before processing
        kids_before = Kinder.objects.count()

        # Process Excel and expect it to fail
        with self.assertRaises(Exception) as context:
            process_excel()

        # Verify the exception is about file not found
        self.assertIn("not found", str(context.exception))

        # Verify that no kids were created due to transaction rollback
        kids_after = Kinder.objects.count()
        self.assertEqual(kids_before, kids_after,
                         "Transaction rollback failed - kids were created despite error")

        print(
            "Transaction rollback test passed - no kids were created when file is missing")

    @patch('budo_app.excelProcessor.models.Kinder')
    def test_transaction_rollback_on_family_assignment_error(self, mock_kinder_class):
        """Test that transaction is rolled back when family assignment fails"""
        # Create a mock kid instance that will fail during family assignment
        mock_kid = MagicMock()
        # First save succeeds, second fails
        mock_kid.save.side_effect = [
            None, Exception("Family assignment failed")]

        # Mock the Kinder class to return our mock instance
        mock_kinder_class.return_value = mock_kid

        # Count kids before processing
        kids_before = Kinder.objects.count()

        # Process Excel and expect it to fail during family assignment
        with self.assertRaises(Exception) as context:
            process_excel()

        # Verify the exception is about family assignment
        self.assertIn("Family assignment failed", str(context.exception))

        # Verify that no kids were created due to transaction rollback
        kids_after = Kinder.objects.count()
        self.assertEqual(kids_before, kids_after,
                         "Transaction rollback failed - kids were created despite error")

        print("Transaction rollback test passed - no kids were created after family assignment error")
