"""Repair stale EXIF on location JPEGs whose pixels were already normalized."""

from functools import partial
import posixpath
from uuid import uuid4

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from budo_app.fields import reset_jpeg_exif_orientation
from budo_app.models import AuslagerorteImage


class Command(BaseCommand):
    help = (
        "Reset stale JPEG EXIF Orientation without re-encoding. Dry-run by default. "
        "Applying requires --assume-normalized: pre-July-9-2024 uploads used a plain "
        "ImageField and cannot be identified automatically. See "
        "docs/operations/location-image-orientation.md."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Write repaired files and update rows.")
        parser.add_argument(
            "--assume-normalized", action="store_true",
            help="Assert that selected files came through django-resized with rotation normalization enabled.",
        )
        parser.add_argument(
            "--image-id", type=int, action="append",
            help="Limit to this AuslagerorteImage primary key (repeatable).",
        )

    def handle(self, *args, **options):
        if options["apply"] and not options["assume_normalized"]:
            raise CommandError(
                "--apply requires --assume-normalized after verifying upload provenance; "
                "legacy plain-ImageField uploads may still need their EXIF rotation."
            )
        self.counts = dict(scanned=0, needs_repair=0, repaired=0, skipped=0, errors=0)
        self.stdout.write("APPLY" if options["apply"] else "DRY RUN (no files or rows will be written)")
        rows = AuslagerorteImage.objects.only("pk", "image").order_by("pk")
        if options["image_id"]:
            rows = rows.filter(pk__in=options["image_id"])
        for photo in rows.iterator(chunk_size=200):
            self.counts["scanned"] += 1
            name, storage = photo.image.name, photo.image.storage
            if not name:
                self.counts["skipped"] += 1
                continue
            try:
                with storage.open(name, "rb") as stored:
                    original = stored.read()
                patched = reset_jpeg_exif_orientation(original)
                if patched is original:
                    self.counts["skipped"] += 1
                    continue
                self.counts["needs_repair"] += 1
                self.stdout.write(f"Needs repair: image={photo.pk}, key={name}")
                if options["apply"]:
                    self._replace(photo, storage, name, patched)
                    self.counts["repaired"] += 1
            except Exception as error:
                self._error(f"image={photo.pk}, key={name}: {error}")
        counts = self.counts
        self.stdout.write(
            f"scanned={counts['scanned']}, needs repair={counts['needs_repair']}, "
            f"repaired={counts['repaired']}, skipped={counts['skipped']}, errors={counts['errors']}"
        )
        if counts["errors"]:
            raise CommandError("Repair finished with errors; see the summary and file keys above.")

    def _error(self, message):
        self.counts["errors"] += 1
        self.stderr.write(message)

    def _replace(self, photo, storage, old_name, data):
        # Never overwrite the old key. Use storage.save()'s returned key, since
        # S3 file_overwrite=False (and filesystem storage) may rename on collision.
        requested_name = posixpath.join(
            posixpath.dirname(old_name), f"orientation-{uuid4().hex}.jpeg"
        )
        new_name = storage.save(
            requested_name, ContentFile(data), max_length=photo.image.field.max_length
        )
        try:
            # Durable prevents a caller's outer transaction from rolling back
            # the row after this method has returned and lost its cleanup scope.
            with transaction.atomic(durable=True):
                changed = AuslagerorteImage.objects.filter(pk=photo.pk, image=old_name).update(image=new_name)
                if changed != 1:
                    raise CommandError("Row changed while repairing; replacement discarded.")
                transaction.on_commit(partial(self._delete_unreferenced, storage, old_name))
        except Exception:
            try:
                storage.delete(new_name)
            except Exception as error:
                self._error(f"Could not remove unused replacement key={new_name}: {error}")
            raise

    def _delete_unreferenced(self, storage, name):
        # Deletion failures cannot roll back a committed row pointing at good
        # bytes. Report the leftover key for cleanup, retaining both copies.
        try:
            if not AuslagerorteImage.objects.filter(image=name).exists():
                storage.delete(name)
        except Exception as error:
            self._error(f"Repaired row committed, but old key={name} could not be deleted: {error}")
