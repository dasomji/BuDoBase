from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.core.files.base import ContentFile
from django.core.management import call_command, CommandError
from django.db import connection
from django.test import TransactionTestCase, override_settings
from PIL import Image

from .fields import reset_jpeg_exif_orientation
from .models import Auslagerorte, AuslagerorteImage


class StorageResponseError(Exception):
    """Exercise S3-style responses without importing boto or contacting storage."""

    def __init__(self, code, status):
        super().__init__(code)
        self.response = {"Error": {"Code": code}, "ResponseMetadata": {"HTTPStatusCode": status}}


# The command's durable=True transaction must be outermost.
class RepairLocationImageOrientationTest(TransactionTestCase):
    def setUp(self):
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media.name,
            STORAGES={"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"}},
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        exif = Image.Exif()
        exif[0x0112] = 6
        exif[0x010F] = "Historic camera"
        source = BytesIO()
        # Already-normalized historic pixels, still carrying the original tag.
        Image.new("RGB", (540, 1080), "red").save(source, format="JPEG", exif=exif)
        self.original = source.getvalue()
        self.storage = AuslagerorteImage._meta.get_field("image").storage
        self.old_name = self.storage.save("auslagerorte_images/old.jpeg", ContentFile(self.original))
        # Assign a stored key directly to reproduce pre-fix data, bypassing save().
        self.photo = AuslagerorteImage.objects.create(
            auslagerort=Auslagerorte.objects.create(name="Historic location"),
            image=self.old_name,
        )

    def run_repair(self, *args, expect_errors=False):
        output, errors = StringIO(), StringIO()
        if expect_errors:
            with self.assertRaisesMessage(CommandError, "finished with errors"):
                call_command("repair_auslagerorte_image_orientation", *args, stdout=output, stderr=errors)
        else:
            call_command("repair_auslagerorte_image_orientation", *args, stdout=output, stderr=errors)
        return output.getvalue(), errors.getvalue()

    def files(self):
        return sorted(path.relative_to(self.media.name) for path in Path(self.media.name).rglob("*") if path.is_file())

    def test_dry_run_does_not_write_files_or_database(self):
        before = self.files()
        with patch.object(self.storage, "save", wraps=self.storage.save) as save, patch.object(
            self.storage, "delete", wraps=self.storage.delete
        ) as delete:
            output, errors = self.run_repair()
            save.assert_not_called()
            delete.assert_not_called()
        self.photo.refresh_from_db()
        self.assertEqual(self.photo.image.name, self.old_name)
        self.assertEqual(self.files(), before)
        with self.storage.open(self.old_name) as stored:
            self.assertEqual(stored.read(), self.original)
        self.assertIn("DRY RUN", output)
        self.assertIn("scanned=1, needs repair=1, repaired=0, skipped=0, skipped_not_resized=0, missing=0, errors=0", output)
        self.assertEqual(errors, "")

    def test_apply_requires_explicit_provenance_assertion(self):
        with self.assertRaisesMessage(CommandError, "--assume-normalized"):
            self.run_repair("--apply")
        self.assertTrue(self.storage.exists(self.old_name))

    def test_apply_replaces_file_updates_row_then_deletes_old_and_is_idempotent(self):
        real_delete = self.storage.delete

        def delete_after_commit(name):
            self.assertFalse(connection.in_atomic_block)
            self.assertFalse(AuslagerorteImage.objects.filter(image=name).exists())
            self.assertTrue(self.storage.exists(AuslagerorteImage.objects.get(pk=self.photo.pk).image.name))
            real_delete(name)

        with patch.object(self.storage, "delete", side_effect=delete_after_commit):
            output, errors = self.run_repair("--apply", "--assume-normalized")
        self.photo.refresh_from_db()
        self.assertNotEqual(self.photo.image.name, self.old_name)
        self.assertFalse(self.storage.exists(self.old_name))
        with self.photo.image.open("rb") as content:
            self.assertEqual(content.read(), reset_jpeg_exif_orientation(self.original))
        self.assertEqual(len(self.files()), 1)
        self.assertIn("scanned=1, needs repair=1, repaired=1, skipped=0, skipped_not_resized=0, missing=0, errors=0", output)
        self.assertEqual(errors, "")
        name = self.photo.image.name
        output, errors = self.run_repair("--apply", "--assume-normalized")
        self.photo.refresh_from_db()
        self.assertEqual(self.photo.image.name, name)
        self.assertEqual(len(self.files()), 1)
        self.assertIn("needs repair=0, repaired=0, skipped=1, skipped_not_resized=0, missing=0, errors=0", output)

    def test_database_failure_removes_replacement_and_retains_original(self):
        with patch("django.db.models.query.QuerySet.update", side_effect=RuntimeError("DB failed")):
            output, errors = self.run_repair("--apply", "--assume-normalized", expect_errors=True)
        self.photo.refresh_from_db()
        self.assertEqual(self.photo.image.name, self.old_name)
        self.assertEqual(self.files(), [Path(self.old_name)])
        self.assertIn("repaired=0, skipped=0, skipped_not_resized=0, missing=0, errors=1", output)
        self.assertIn("DB failed", errors)

    def test_concurrent_row_change_does_not_delete_either_referenced_file(self):
        with patch("django.db.models.query.QuerySet.update", return_value=0):
            output, errors = self.run_repair("--apply", "--assume-normalized", expect_errors=True)
        self.assertEqual(self.files(), [Path(self.old_name)])
        self.assertIn("errors=1", output)
        self.assertIn("changed", errors)

    def test_missing_file_is_reported_and_other_rows_are_scanned(self):
        missing = AuslagerorteImage.objects.create(
            auslagerort=self.photo.auslagerort, image="missing.jpeg"
        )
        # Process the missing row first to prove later rows still get repaired.
        missing.image, self.photo.image = self.photo.image.name, missing.image.name
        missing.save(update_fields=["image"])
        self.photo.save(update_fields=["image"])
        for args in ((), ("--apply", "--assume-normalized")):
            with self.subTest(args=args):
                output, errors = self.run_repair(*args, expect_errors=True)
                self.assertIn("scanned=2, needs repair=1", output)
                self.assertIn("missing=1, errors=1", output)
                self.assertIn(f"image={self.photo.pk}", errors)
                self.assertIn("missing.jpeg", errors)
                self.photo.refresh_from_db()
                self.assertEqual(self.photo.image.name, "missing.jpeg")
                missing.refresh_from_db()
                if args:
                    self.assertIn("repaired=1", output)
                    with missing.image.open("rb") as stored:
                        self.assertEqual(stored.read(), reset_jpeg_exif_orientation(self.original))
                else:
                    self.assertEqual(missing.image.name, self.old_name)

    def test_oversized_legacy_jpeg_is_skipped_without_decoding_or_reading_all_bytes(self):
        source = BytesIO()
        exif = Image.Exif()
        exif[0x0112] = 6
        Image.new("RGB", (4000, 3000), "blue").save(source, format="JPEG", exif=exif)
        original = source.getvalue()
        name = self.storage.save("legacy.jpeg", ContentFile(original))
        legacy = AuslagerorteImage.objects.create(auslagerort=self.photo.auslagerort, image=name)
        real_open = self.storage.open

        def header_only_open(*args, **kwargs):
            stored = real_open(*args, **kwargs)
            real_read = stored.read

            def read(size=-1):
                self.assertGreaterEqual(size, 0, "Legacy file must only have its header read")
                return real_read(size)

            stored.file = Mock(wraps=stored.file)
            stored.file.read.side_effect = read
            return stored

        for args in ((), ("--apply", "--assume-normalized")):
            with self.subTest(args=args), patch.object(self.storage, "open", side_effect=header_only_open), patch.object(
                Image.Image, "load", side_effect=AssertionError("Must not decode pixels")
            ), patch.object(self.storage, "save") as save, patch.object(self.storage, "delete") as delete:
                output, errors = self.run_repair(*args, "--image-id", str(legacy.pk), "--verbosity", "2")
                save.assert_not_called()
                delete.assert_not_called()
                self.assertIn("needs repair=0, repaired=0", output)
                self.assertIn("skipped_not_resized=1", output)
                self.assertIn(f"image={legacy.pk}", output)
                self.assertEqual(errors, "")
            legacy.refresh_from_db()
            self.assertEqual(legacy.image.name, name)
            with real_open(name) as stored:
                self.assertEqual(stored.read(), original)

    def test_provenance_limit_comes_from_model_field_size(self):
        field = AuslagerorteImage._meta.get_field("image")
        with patch.object(field, "size", [500, 500]):
            output, errors = self.run_repair("--apply", "--assume-normalized")
        self.assertIn("skipped_not_resized=1", output)
        self.photo.refresh_from_db()
        self.assertEqual(self.photo.image.name, self.old_name)
        self.assertEqual(errors, "")

    def test_unreadable_and_s3_errors_are_reported_without_aborting(self):
        bad = AuslagerorteImage.objects.create(auslagerort=self.photo.auslagerort, image="bad.jpeg")
        real_open = self.storage.open
        for error, missing in (
            (OSError("unreadable"), 0),
            (StorageResponseError("NoSuchKey", 404), 1),
            (StorageResponseError("AccessDenied", 403), 0),
        ):
            def open_or_raise(name, *args, **kwargs):
                if name == bad.image.name:
                    raise error
                return real_open(name, *args, **kwargs)

            with self.subTest(error=error), patch.object(self.storage, "open", side_effect=open_or_raise):
                output, errors = self.run_repair(expect_errors=True)
                self.assertIn("scanned=2, needs repair=1", output)
                self.assertIn(f"missing={missing}, errors=1", output)
                self.assertIn(f"image={bad.pk}", errors)

    def test_unidentified_image_is_reported_and_other_rows_continue(self):
        name = self.storage.save("broken.jpeg", ContentFile(b"not an image"))
        bad = AuslagerorteImage.objects.create(auslagerort=self.photo.auslagerort, image=name)
        output, errors = self.run_repair(expect_errors=True)
        self.assertIn("scanned=2, needs repair=1", output)
        self.assertIn("missing=0, errors=1", output)
        self.assertIn(f"image={bad.pk}", errors)

    def test_query_does_not_use_a_server_side_cursor(self):
        with patch("django.db.models.query.QuerySet.iterator", side_effect=AssertionError("No server cursor")):
            output, errors = self.run_repair()
        self.assertIn("needs repair=1", output)
        self.assertEqual(errors, "")

    def test_failure_after_commit_never_deletes_referenced_replacement(self):
        with patch(
            "budo_app.management.commands.repair_auslagerorte_image_orientation.Command._delete_unreferenced",
            side_effect=RuntimeError("post-commit failure"),
        ):
            output, errors = self.run_repair("--apply", "--assume-normalized", expect_errors=True)
        self.photo.refresh_from_db()
        self.assertNotEqual(self.photo.image.name, self.old_name)
        self.assertTrue(self.storage.exists(self.photo.image.name))
        self.assertTrue(self.storage.exists(self.old_name))
        self.assertIn("post-commit failure", errors)

    def test_deletion_failure_retains_the_repaired_row_and_reports_old_key(self):
        with patch.object(self.storage, "delete", side_effect=OSError("delete failed")):
            output, errors = self.run_repair("--apply", "--assume-normalized", expect_errors=True)
        self.photo.refresh_from_db()
        self.assertNotEqual(self.photo.image.name, self.old_name)
        self.assertTrue(self.storage.exists(self.old_name))
        self.assertTrue(self.storage.exists(self.photo.image.name))
        self.assertIn("repaired=1, skipped=0, skipped_not_resized=0, missing=0, errors=1", output)
        self.assertIn(self.old_name, errors)

    def test_shared_old_file_is_kept_until_all_references_are_repaired(self):
        second = AuslagerorteImage.objects.create(auslagerort=self.photo.auslagerort, image=self.old_name)
        output, errors = self.run_repair(
            "--apply", "--assume-normalized", "--image-id", str(self.photo.pk)
        )
        self.assertTrue(self.storage.exists(self.old_name))
        output, errors = self.run_repair(
            "--apply", "--assume-normalized", "--image-id", str(second.pk)
        )
        self.assertFalse(self.storage.exists(self.old_name))
        self.assertEqual(errors, "")
