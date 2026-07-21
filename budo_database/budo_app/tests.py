from django.test import TestCase, Client, SimpleTestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from .forms import AuslagerorteImageForm
from .models import Auslagerorte, AuslagerorteImage, Document, Turnus, Kinder
from .excelProcessor import (
    parse_birthday,
    parse_budo_erfahrung,
    process_excel,
    validate_workbook_columns,
)
from unittest.mock import patch
from django.contrib.auth.models import User
from io import BytesIO
from tempfile import TemporaryDirectory
import os
import json
import pandas as pd
from PIL import Image
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


def make_image_upload(name="location.png", size=(1200, 600), color="red"):
    source = BytesIO()
    Image.new("RGB", size, color).save(source, format="PNG")
    return SimpleUploadedFile(
        name,
        source.getvalue(),
        content_type="image/png",
    )


def sample_excel_frames():
    budo = pd.DataFrame([{
        "Index": "T1-1",
        "AnreiseText": "Betreute Anreise, Top Jugendticket vorhanden",
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


class ExcelValueParsingTest(SimpleTestCase):
    def test_uppercase_ja_is_parsed_as_previous_budo_experience(self):
        for value in ("JA", "JA\n", "JA, mehrmals \n"):
            with self.subTest(value=value):
                self.assertIs(parse_budo_erfahrung(value), True)


class AuslagerorteImageTest(TestCase):
    def test_uploaded_image_is_resized_and_converted_to_jpeg(self):
        upload = make_image_upload()

        with (
            TemporaryDirectory() as media_root,
            override_settings(MEDIA_ROOT=media_root),
        ):
            location = Auslagerorte.objects.create(name="Test location")
            stored_image = AuslagerorteImage.objects.create(
                auslagerort=location,
                image=upload,
            )

            self.assertTrue(stored_image.image.name.endswith(".jpeg"))
            self.assertTrue(
                AuslagerorteImage._meta.get_field("image").keep_meta
            )
            with stored_image.image.open("rb") as stored_file:
                with Image.open(stored_file) as resized_image:
                    self.assertEqual(resized_image.format, "JPEG")
                    self.assertEqual(resized_image.size, (1080, 540))


    def test_uploaded_image_keeps_gps_metadata(self):
        source = BytesIO()
        image = Image.new("RGB", (100, 100), "red")
        exif = Image.Exif()
        exif[0x8825] = {
            1: "N",
            2: (48.0, 12.0, 0.0),
            3: "E",
            4: (16.0, 22.0, 0.0),
        }
        image.save(source, format="JPEG", exif=exif)
        upload = SimpleUploadedFile(
            "gps.jpeg",
            source.getvalue(),
            content_type="image/jpeg",
        )

        with (
            TemporaryDirectory() as media_root,
            override_settings(MEDIA_ROOT=media_root),
        ):
            location = Auslagerorte.objects.create(name="GPS location")
            stored_image = AuslagerorteImage.objects.create(
                auslagerort=location,
                image=upload,
            )

            with stored_image.image.open("rb") as stored_file:
                with Image.open(stored_file) as resized_image:
                    gps = resized_image.getexif().get_ifd(0x8825)

        self.assertEqual(gps[1], "N")
        self.assertEqual(gps[3], "E")


class AuslagerorteImageFormTest(TestCase):
    def test_images_are_required_and_must_be_decodable(self):
        empty_form = AuslagerorteImageForm(data={}, files={})
        invalid_form = AuslagerorteImageForm(
            data={},
            files={
                "images": SimpleUploadedFile(
                    "not-an-image.txt",
                    b"not an image",
                    content_type="text/plain",
                )
            },
        )

        self.assertFalse(empty_form.is_valid())
        self.assertFalse(invalid_form.is_valid())

    @override_settings(LOCATION_IMAGE_MAX_FILES=1)
    def test_image_count_limit_is_enforced(self):
        form = AuslagerorteImageForm(
            data={},
            files={"images": [make_image_upload(), make_image_upload()]},
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors.as_data()["images"][0].code, "too_many_images")

    @override_settings(
        LOCATION_IMAGE_MAX_FILE_SIZE=100_000,
        LOCATION_IMAGE_MAX_TOTAL_SIZE=100,
    )
    def test_aggregate_size_limit_is_enforced(self):
        form = AuslagerorteImageForm(
            data={},
            files={
                "images": [
                    make_image_upload(name="one.png", size=(20, 20)),
                    make_image_upload(name="two.png", size=(20, 20)),
                ]
            },
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors.as_data()["images"][0].code, "images_too_large")

    def test_per_file_size_limit_is_enforced(self):
        upload = make_image_upload(size=(20, 20))
        with override_settings(
            LOCATION_IMAGE_MAX_FILE_SIZE=upload.size - 1,
            LOCATION_IMAGE_MAX_TOTAL_SIZE=upload.size * 2,
        ):
            form = AuslagerorteImageForm(
                data={},
                files={"images": upload},
            )
            is_valid = form.is_valid()

        self.assertFalse(is_valid)
        self.assertEqual(form.errors.as_data()["images"][0].code, "image_too_large")

    @override_settings(LOCATION_IMAGE_MAX_PIXELS=100)
    def test_decoded_pixel_limit_is_enforced(self):
        form = AuslagerorteImageForm(
            data={},
            files={"images": make_image_upload(size=(11, 10))},
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors.as_data()["images"][0].code, "too_many_pixels")


class AuslagerorteImageUploadTest(TestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        self.media_override = override_settings(
            MEDIA_ROOT=self.media_directory.name,
        )
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)

        self.user = User.objects.create_user(
            username="image-uploader",
            password="testpass123",
        )
        self.client.login(username="image-uploader", password="testpass123")
        self.location = Auslagerorte.objects.create(name="Test location")
        self.url = reverse(
            "auslagerorte-image-upload",
            kwargs={"pk": self.location.pk},
        )

    def stored_file_names(self):
        return [
            filename
            for _, _, filenames in os.walk(self.media_directory.name)
            for filename in filenames
        ]

    def test_two_valid_images_create_two_records_and_objects(self):
        response = self.client.post(
            self.url,
            {
                "images": [
                    make_image_upload(name="one.png"),
                    make_image_upload(name="two.png", color="blue"),
                ]
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.location.images.count(), 2)
        self.assertEqual(len(self.stored_file_names()), 2)

    def test_failed_batch_removes_records_and_already_written_objects(self):
        original_save = AuslagerorteImage.save
        save_calls = 0

        def fail_second_save(instance, *args, **kwargs):
            nonlocal save_calls
            save_calls += 1
            if save_calls == 2:
                raise RuntimeError("simulated storage failure")
            return original_save(instance, *args, **kwargs)

        with patch.object(AuslagerorteImage, "save", new=fail_second_save):
            response = self.client.post(
                self.url,
                {
                    "images": [
                        make_image_upload(name="one.png"),
                        make_image_upload(name="two.png", color="blue"),
                    ]
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "konnten nicht gespeichert werden")
        self.assertEqual(self.location.images.count(), 0)
        self.assertEqual(self.stored_file_names(), [])


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
        self.media_directory = TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        self.media_override = override_settings(
            MEDIA_ROOT=self.media_directory.name,
        )
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)

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
        self.assertTrue(
            turnus.uploadedFile.storage.exists(turnus.uploadedFile.name)
        )
        process_excel_mock.assert_called_once_with(turnus)


class StorageLifecycleTest(TestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        self.media_override = override_settings(
            MEDIA_ROOT=self.media_directory.name,
        )
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)

    def test_deleting_an_image_record_deletes_its_stored_object(self):
        location = Auslagerorte.objects.create(name="Test location")
        stored_image = AuslagerorteImage.objects.create(
            auslagerort=location,
            image=make_image_upload(),
        )
        storage = stored_image.image.storage
        name = stored_image.image.name

        with self.captureOnCommitCallbacks(execute=True):
            stored_image.delete()

        self.assertFalse(storage.exists(name))

    def test_deleting_a_turnus_deletes_its_stored_workbook(self):
        turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2024, 7, 1),
            uploadedFile=SimpleUploadedFile("workbook.xlsx", b"workbook"),
        )
        storage = turnus.uploadedFile.storage
        name = turnus.uploadedFile.name

        with self.captureOnCommitCallbacks(execute=True):
            turnus.delete()

        self.assertFalse(storage.exists(name))

    def test_replacing_a_document_deletes_its_previous_object(self):
        document = Document.objects.create(
            title="Test document",
            uploadedFile=SimpleUploadedFile("old.txt", b"old"),
        )
        storage = document.uploadedFile.storage
        old_name = document.uploadedFile.name
        document.uploadedFile = SimpleUploadedFile("new.txt", b"new")

        with self.captureOnCommitCallbacks(execute=True):
            document.save()

        self.assertFalse(storage.exists(old_name))
        self.assertTrue(storage.exists(document.uploadedFile.name))


class TurnusWorkbookReplacementTest(TestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        self.media_override = override_settings(
            MEDIA_ROOT=self.media_directory.name,
        )
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)

        self.user = User.objects.create_user(
            username="workbook-uploader",
            password="testpass123",
        )
        self.client.login(
            username="workbook-uploader",
            password="testpass123",
        )
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2024, 7, 1),
            uploadedFile=SimpleUploadedFile("old.xlsx", b"old workbook"),
        )
        self.old_name = self.turnus.uploadedFile.name
        self.storage = self.turnus.uploadedFile.storage
        self.url = reverse(
            "upload_excel",
            kwargs={"turnus_id": self.turnus.pk},
        )

    def replacement_data(self):
        return {
            "turnus_nr": 1,
            "turnus_beginn": "2024-07-01",
            "uploadedFile": SimpleUploadedFile(
                "new.xlsx",
                b"new workbook",
                content_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
            ),
        }

    @patch("budo_app.excel_views.process_excel")
    def test_successful_replacement_deletes_old_workbook(self, process_excel_mock):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, self.replacement_data())

        self.assertEqual(response.status_code, 302)
        self.turnus.refresh_from_db()
        self.assertNotEqual(self.turnus.uploadedFile.name, self.old_name)
        self.assertFalse(self.storage.exists(self.old_name))
        self.assertTrue(self.storage.exists(self.turnus.uploadedFile.name))
        process_excel_mock.assert_called_once()

    @patch(
        "budo_app.excel_views.process_excel",
        side_effect=ValueError("invalid workbook"),
    )
    def test_failed_replacement_keeps_old_and_deletes_new_workbook(
        self,
        process_excel_mock,
    ):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, self.replacement_data())

        self.assertEqual(response.status_code, 200)
        self.turnus.refresh_from_db()
        self.assertEqual(self.turnus.uploadedFile.name, self.old_name)
        self.assertTrue(self.storage.exists(self.old_name))
        stored_names = [
            os.path.relpath(os.path.join(root, filename), self.media_directory.name)
            for root, _, filenames in os.walk(self.media_directory.name)
            for filename in filenames
        ]
        self.assertEqual(stored_names, [self.old_name])
        process_excel_mock.assert_called_once()


class DownloadUpdatedExcelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="download-user",
            password="testpass123",
        )
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2024, 7, 1),
        )
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.client.login(username="download-user", password="testpass123")

    def test_generated_download_uses_a_cleaned_up_temporary_file(self):
        generated_path = None

        def generate_file(path, turnus):
            nonlocal generated_path
            generated_path = path
            with open(path, "wb") as generated_file:
                generated_file.write(b"generated workbook")

        with patch(
            "budo_app.excel_views.update_excel_file",
            side_effect=generate_file,
        ):
            response = self.client.get(reverse("download_updated_excel"))
            content = b"".join(response.streaming_content)
            response.close()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(content, b"generated workbook")
        self.assertIsNotNone(generated_path)
        self.assertFalse(os.path.exists(os.path.dirname(generated_path)))


class ExcelProcessingTransactionTest(TestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        self.media_override = override_settings(
            MEDIA_ROOT=self.media_directory.name,
        )
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)

        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2024, 7, 1),
            uploadedFile=SimpleUploadedFile(
                "detail_test.xlsx",
                b"test workbook placeholder",
            ),
        )

    @patch('budo_app.excelProcessor.read_workbook')
    def test_successful_processing_with_selected_turnus(self, mock_read_workbook):
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
        self.assertTrue(first_kid.top_jugendticket)

    @patch('budo_app.excelProcessor.read_workbook')
    def test_top_jugendticket_is_imported_from_anreise_text(
            self, mock_read_workbook):
        budo, budo_raw = sample_excel_frames()
        budo.loc[0, "AnreiseText"] = (
            "Ja, betreute Anreise und Top Jugendticket vorhanden"
        )
        budo.loc[0, "AbreiseText"] = "Betreute Abreise"
        mock_read_workbook.return_value = (budo, budo_raw)

        process_excel(self.turnus)

        kid = Kinder.objects.get(turnus=self.turnus)
        self.assertTrue(kid.top_jugendticket)

    @patch('budo_app.excelProcessor.read_workbook')
    def test_no_top_jugendticket_is_not_imported_as_ticket(
            self, mock_read_workbook):
        budo, budo_raw = sample_excel_frames()
        budo.loc[0, "AnreiseText"] = (
            "Betreute Anreise, kein Top Jugendticket vorhanden"
        )
        budo.loc[0, "AbreiseText"] = "Betreute Abreise"
        mock_read_workbook.return_value = (budo, budo_raw)

        process_excel(self.turnus)

        kid = Kinder.objects.get(turnus=self.turnus)
        self.assertFalse(kid.top_jugendticket)

    @patch('budo_app.excelProcessor.read_workbook')
    @patch('budo_app.models.Kinder.save')
    def test_transaction_rollback_on_save_error(self, mock_save, mock_read_workbook):
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

    @patch('budo_app.excelProcessor.read_workbook')
    def test_transaction_rollback_on_excel_read_error(self, mock_read_workbook):
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

    @patch('budo_app.excelProcessor.read_workbook')
    @patch('budo_app.excelProcessor.from_excel_ordinal')
    def test_transaction_rollback_on_date_parsing_error(self, mock_date_parser, mock_read_workbook):
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

    @patch('budo_app.excelProcessor.read_workbook')
    @patch('budo_app.excelProcessor.assign_budo_families')
    def test_transaction_rollback_on_family_assignment_error(self, mock_assign, mock_read_workbook):
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

    @patch('budo_app.excelProcessor.read_workbook')
    def test_invalid_birthday_reports_expected_formats(self, mock_read_workbook):
        budo, budo_raw = sample_excel_frames()
        budo.loc[0, "Kind_Geburtsdatum"] = "not-a-date"
        mock_read_workbook.return_value = (budo, budo_raw)

        with self.assertRaises(ValueError) as context:
            process_excel(self.turnus)

        self.assertIn("Invalid birthday", str(context.exception))
        self.assertIn("DD.MM.YYYY", str(context.exception))

    def test_numeric_text_birthday_is_parsed_as_excel_ordinal(self):
        self.assertEqual(parse_birthday("39893"), date(2009, 3, 21))

    @patch('budo_app.excelProcessor.read_workbook')
    def test_postal_code_with_locality_is_imported(self, mock_read_workbook):
        budo, budo_raw = sample_excel_frames()
        budo["Rechnung_PLZ"] = budo["Rechnung_PLZ"].astype(object)
        budo.loc[0, "Rechnung_PLZ"] = "3420 Kritzendorf"
        mock_read_workbook.return_value = (budo, budo_raw)

        process_excel(self.turnus)

        kid = Kinder.objects.get(turnus=self.turnus)
        self.assertEqual(kid.rechnung_plz, 3420)
