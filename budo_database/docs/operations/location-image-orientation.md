# Repair location JPEG orientation

Issue [#206](https://github.com/dasomji/BuDoBase/issues/206) affected JPEG uploads
to `AuslagerorteImage.image`: django-resized normalized the pixels but retained
the original EXIF Orientation. The field now resets the final JPEG's IFD0
Orientation SHORT to 1 without re-encoding. All other bytes remain unchanged.
XMP `tiff:Orientation` may still say 6; browsers ignore XMP orientation, so this
remaining metadata is cosmetic.
PNG and HEIF uploads still use the same resize/convert pipeline. First-aid
photos already use `ImageOps.exif_transpose()` and encode metadata-free WebP;
they do not need this repair.

## Establish provenance before applying

The repository's requirements history has only two django-resized versions:

| Version | Introduced | Published source |
| --- | --- | --- |
| 1.0.2 | `e555a57`, 2024-07-09 (also introduced the resized field) | [PyPI wheel](https://files.pythonhosted.org/packages/05/ef/a3ad9941f14a13a5dc9f2bdc8992bf21cc09c462c718711a0281acfab67c/django_resized-1.0.2-py3-none-any.whl) |
| 1.0.3 | `a1295be`, 2024-11-13 | [PyPI wheel](https://files.pythonhosted.org/packages/38/ac/3495743e9923a3b79a929782f63db7acd606dc94c15c296487ef6d015717/django_resized-1.0.3-py3-none-any.whl) |

Both wheels' `django_resized/forms.py` define
`DEFAULT_NORMALIZE_ROTATION = getattr(settings, 'DJANGORESIZED_DEFAULT_NORMALIZE_ROTATION', True)`
and call `normalize_rotation(img)` before resizing when it is enabled. The
function handles orientations 2–8, including mirrors. Both also default
`keep_meta` to True. No repository settings history overrides normalization.
For JPEGs saved through this pipeline, non-1 Orientation describes a transform
already applied to the pixels, so resetting it is safe.

However, `053c808` introduced location images with a plain `ImageField` on
2024-07-03. Files uploaded before the deployment of commit e555a57 (2024-07-09),
direct imports, or files saved with normalization disabled may still need their
orientation tag. The commit date does not establish the deployment date. The
model has no upload timestamp or processing provenance.

The command applies two layers of protection:

1. Automatically read the image header's dimensions and skip files whose larger
   dimension exceeds the model field's `size` limit (currently 1080). The resized
   pipeline cannot produce these files. They are counted as `skipped_not_resized`;
   use `--verbosity 2` to list their row ids and keys. This check does not decode
   pixels. Local storage reads only the header for this size check. With
   django-storages S3, the first read downloads the whole object into a spooled
   temporary file, which subsequent reads reuse. A dry run over S3 therefore
   transfers every image once, including oversized files that are skipped.
2. For files at or below that limit, applying requires `--assume-normalized`.
   Smaller plain-ImageField legacy uploads remain ambiguous: dimensions and EXIF
   cannot prove that pixels have already been normalized. The flag is an operator
   assertion that the remaining selected files went through the normalization
   pipeline. Establish this from upload or deployment records, known migration
   history, or visual inspection. Use repeatable `--image-id` to restrict scope
   to verified rows. Do not assert normalization for an unknown legacy collection.

## Command

Use the normal environment and storage configuration for the intended database.
Dry-run is the default and writes neither files nor rows:

```bash
python manage.py repair_auslagerorte_image_orientation
python manage.py repair_auslagerorte_image_orientation --image-id 123 --image-id 456
```

After establishing provenance, apply to verified rows:

```bash
python manage.py repair_auslagerorte_image_orientation --apply --assume-normalized --image-id 123
```

Omit `--image-id` only when every file passing the automatic size filter is
verified. Run `--apply` during a quiet window: a concurrent admin save of the
same image could re-point a row at the old key after the repair commits.

No image pixels are decoded or re-encoded. Recognized non-JPEG images and
absent/already-normal or unsupported EXIF are left untouched and counted as
`skipped`. Unreadable files, including headers PIL cannot identify, are errors.
Dry-run candidates mean “the bytes can be patched,” not proof of processing
provenance.

The summary reports scanned, needs repair, repaired, skipped,
`skipped_not_resized`, `missing`, and errors. Missing files are included in both
`missing` and errors. Each error includes the affected row id/file key and makes
the command exit nonzero after processing the remaining rows. This includes
filesystem errors and S3 not-found/download errors. A second run skips repaired
files.

Production S3 has `file_overwrite=False`. For each repair the command:

1. Saves patched bytes under a new UUID-based name via the field's storage and
   uses the actual returned storage key.
2. Updates the row inside a durable transaction, conditional on its old key
   still matching. On a concurrent edit or transaction error, retains the old
   key and deletes the replacement only after confirming no row references it.
   A commit can succeed even if its acknowledgement fails; a referenced
   replacement is retained. If the reference check fails, both keys are kept
   and stderr reports the row id and both keys as needing manual review.
3. Deletes the old key after commit, only if no location-image row references
   it. A deletion failure leaves the repaired row valid and reports the old key
   for cleanup. Failed replacement cleanup is also reported with its key.

Storage and database operations cannot form one atomic transaction. A process
crash or an ambiguous remote save response can leave an unreferenced object;
the command prioritizes retaining referenced data. Do not run alongside bulk
imports that reuse existing storage keys.

## Migration

`0100_normalize_location_image_orientation` records the real custom field path.
Django 6.1 compares field class paths, so its automatically generated bare
`AlterField` rebuilds the SQLite table despite identical column definitions.
The migration therefore wraps that `AlterField` in
`SeparateDatabaseAndState(database_operations=[])`. `sqlmigrate` emits only a
no-op comment and transaction boundaries; no schema or data SQL is executed.
