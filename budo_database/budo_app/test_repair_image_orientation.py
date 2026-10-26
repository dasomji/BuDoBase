from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.management import call_command, CommandError
from django.test import TransactionTestCase, override_settings
from PIL import Image

from .fields import reset_jpeg_exif_orientation
from .models import Auslagerorte, AuslagerorteImage


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
        self.assertIn("scanned=1, needs repair=1, repaired=0, skipped=0, errors=0", output)
        self.assertEqual(errors, "")

    def test_apply_requires_explicit_provenance_assertion(self):
        with self.assertRaisesMessage(CommandError, "--assume-normalized"):
            self.run_repair("--apply")
        self.assertTrue(self.storage.exists(self.old_name))

    def test_apply_replaces_file_updates_row_then_deletes_old_and_is_idempotent(self):
        real_delete = self.storage.delete

        def delete_after_commit(name):
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
        self.assertIn("scanned=1, needs repair=1, repaired=1, skipped=0, errors=0", output)
        self.assertEqual(errors, "")
        name = self.photo.image.name
        output, errors = self.run_repair("--apply", "--assume-normalized")
        self.photo.refresh_from_db()
        self.assertEqual(self.photo.image.name, name)
        self.assertEqual(len(self.files()), 1)
        self.assertIn("needs repair=0, repaired=0, skipped=1, errors=0", output)

    def test_database_failure_removes_replacement_and_retains_original(self):
        with patch("django.db.models.query.QuerySet.update", side_effect=RuntimeError("DB failed")):
            output, errors = self.run_repair("--apply", "--assume-normalized", expect_errors=True)
        self.photo.refresh_from_db()
        self.assertEqual(self.photo.image.name, self.old_name)
        self.assertEqual(self.files(), [Path(self.old_name)])
        self.assertIn("repaired=0, skipped=0, errors=1", output)
        self.assertIn("DB failed", errors)

    def test_concurrent_row_change_does_not_delete_either_referenced_file(self):
        with patch("django.db.models.query.QuerySet.update", return_value=0):
            output, errors = self.run_repair("--apply", "--assume-normalized", expect_errors=True)
        self.assertEqual(self.files(), [Path(self.old_name)])
        self.assertIn("errors=1", output)
        self.assertIn("changed", errors)

    def test_missing_file_is_reported_and_other_rows_are_scanned(self):
        AuslagerorteImage.objects.create(auslagerort=self.photo.auslagerort, image="missing.jpeg")
        output, errors = self.run_repair(expect_errors=True)
        self.assertIn("scanned=2, needs repair=1, repaired=0, skipped=0, errors=1", output)
        self.assertIn("missing.jpeg", errors)

    def test_deletion_failure_retains_the_repaired_row_and_reports_old_key(self):
        with patch.object(self.storage, "delete", side_effect=OSError("delete failed")):
            output, errors = self.run_repair("--apply", "--assume-normalized", expect_errors=True)
        self.photo.refresh_from_db()
        self.assertNotEqual(self.photo.image.name, self.old_name)
        self.assertTrue(self.storage.exists(self.old_name))
        self.assertTrue(self.storage.exists(self.photo.image.name))
        self.assertIn("repaired=1, skipped=0, errors=1", output)
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
