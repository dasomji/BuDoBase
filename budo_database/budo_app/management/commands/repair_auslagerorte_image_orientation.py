"""Repair stale EXIF on location JPEGs whose pixels were already normalized."""

import posixpath
from uuid import uuid4

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image

from budo_app.fields import reset_jpeg_exif_orientation
from budo_app.models import AuslagerorteImage


class Command(BaseCommand):
    help = (
        "Reset stale JPEG EXIF Orientation without re-encoding. Dry-run by default. "
        "Automatically skip images larger than the model field's resize limit. "
        "Applying requires --assume-normalized for smaller files: uploads before "
        "the deployment of commit e555a57 (2024-07-09) used a plain ImageField "
        "and may still need their orientation. See "
        "docs/operations/location-image-orientation.md."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Write repaired files and update rows.")
        parser.add_argument(
            "--assume-normalized", action="store_true",
            help=(
                "After the automatic size filter, assert that the remaining files came "
                "through django-resized with rotation normalization enabled; legacy "
                "files at or below the resize limit remain ambiguous."
            ),
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
        self.counts = dict(
            scanned=0, needs_repair=0, repaired=0, skipped=0,
            skipped_not_resized=0, missing=0, errors=0,
        )
        self.stdout.write("APPLY" if options["apply"] else "DRY RUN (no files or rows will be written)")
        field = AuslagerorteImage._meta.get_field("image")
        storage = field.storage
        resize_limit = max(dimension for dimension in field.size if dimension is not None)
        rows = AuslagerorteImage.objects.order_by("pk")
        if options["image_id"]:
            rows = rows.filter(pk__in=options["image_id"])
        # Load this small collection up front; server-side cursors are unsafe
        # behind transaction-mode connection poolers.
        rows = list(rows.values_list("pk", "image"))
        for image_id, name in rows:
            self.counts["scanned"] += 1
            if not name:
                self.counts["skipped"] += 1
                continue
            try:
                with storage.open(name, "rb") as stored:
                    # Inspect only the header; never decode or transpose pixels.
                    with Image.open(stored) as image:
                        dimensions = image.size
                    if max(dimensions) > resize_limit:
                        self.counts["skipped_not_resized"] += 1
                        if options["verbosity"] >= 2:
                            self.stdout.write(
                                f"Skipped not resized: image={image_id}, key={name}, size={dimensions}"
                            )
                        continue
                    stored.seek(0)
                    original = stored.read()
                patched = reset_jpeg_exif_orientation(original)
                if patched is None:
                    self.counts["skipped"] += 1
                    continue
                self.counts["needs_repair"] += 1
                self.stdout.write(f"Needs repair: image={image_id}, key={name}")
                if options["apply"]:
                    self._replace(image_id, field, name, patched)
                    self.counts["repaired"] += 1
            except Exception as error:
                # django-storages maps open-time S3 404s to FileNotFoundError.
                # Downloads can also raise ClientError; inspect its response
                # without requiring a particular storage backend's exception type.
                response = getattr(error, "response", {})
                missing = isinstance(error, FileNotFoundError) or (
                    response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404
                    or response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}
                )
                if missing:
                    self.counts["missing"] += 1
                self._error(f"{'Missing file' if missing else 'Error'}: image={image_id}, key={name}: {error}")
        counts = self.counts
        self.stdout.write(
            f"scanned={counts['scanned']}, needs repair={counts['needs_repair']}, "
            f"repaired={counts['repaired']}, skipped={counts['skipped']}, "
            f"skipped_not_resized={counts['skipped_not_resized']}, "
            f"missing={counts['missing']}, errors={counts['errors']}"
        )
        if counts["errors"]:
            raise CommandError("Repair finished with errors; see the summary and file keys above.")

    def _error(self, message):
        self.counts["errors"] += 1
        self.stderr.write(message)

    def _replace(self, image_id, field, old_name, data):
        storage = field.storage
        # Never overwrite the old key. Use storage.save()'s returned key, since
        # S3 file_overwrite=False (and filesystem storage) may rename on collision.
        requested_name = posixpath.join(
            posixpath.dirname(old_name), f"orientation-{uuid4().hex}.jpeg"
        )
        new_name = storage.save(
            requested_name, ContentFile(data), max_length=field.max_length
        )
        try:
            # durable=True asserts an outermost transaction, so commit failures
            # stay in this cleanup scope. Tests therefore use TransactionTestCase.
            with transaction.atomic(durable=True):
                changed = AuslagerorteImage.objects.filter(pk=image_id, image=old_name).update(image=new_name)
                if changed != 1:
                    raise CommandError("Row changed while repairing; replacement discarded.")
        except Exception:
            try:
                storage.delete(new_name)
            except Exception as error:
                self._error(f"Could not remove unused replacement key={new_name}: {error}")
            raise
        # The row is committed. Old-key cleanup must never delete the new key
        # if deletion (or its error reporting) fails.
        self._delete_unreferenced(storage, old_name)

    def _delete_unreferenced(self, storage, name):
        # Deletion failures cannot roll back a committed row pointing at good
        # bytes. Report the leftover key for cleanup, retaining both copies.
        try:
            if not AuslagerorteImage.objects.filter(image=name).exists():
                storage.delete(name)
        except Exception as error:
            self._error(f"Repaired row committed, but old key={name} could not be deleted: {error}")
