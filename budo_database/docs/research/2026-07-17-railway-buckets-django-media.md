# Railway Buckets for Django user media

Date: 2026-07-17

## Executive recommendation

Use a Railway Storage Bucket as Django's **production `default` storage** through `django-storages`' `S3Storage` backend. Keep static assets on WhiteNoise and local development media on `FileSystemStorage`.

Keep the bucket private and let `FieldFile.url` generate short-lived presigned GET URLs. This fits the existing templates and React API, which already use `image.image.url`. Do **not** disable query-string authentication: Railway does not currently support public buckets.

Before changing the backend, refactor the Excel importer so it opens `Turnus.uploadedFile` through Django's storage API rather than constructing a local filesystem path. Existing files must then be copied to the bucket under their existing field names; changing `STORAGES` does not migrate bytes.

The location-image UI already selects and submits multiple files correctly, but its server-side form is not production-ready: it accepts empty submissions and arbitrary non-image files, has no count/size limits, can leave partial uploads, and has no multi-upload tests.

## Primary-source facts

- Railway Buckets are private, S3-compatible object storage. Public buckets are not supported. Files can be served with presigned URLs or proxied by the application. Railway says presigned URLs can live for up to 90 days. [Railway Storage Buckets](https://docs.railway.com/storage-buckets), [Uploading & Serving Files](https://docs.railway.com/storage-buckets/uploading-serving)
- New Railway buckets normally use virtual-hosted-style URLs with a base endpoint such as `https://storage.railway.app`; older buckets may require path style. The bucket's Credentials tab is the source of truth. [Railway Storage Buckets](https://docs.railway.com/storage-buckets)
- The S3 API bucket name is `BUCKET`, not `RAILWAY_BUCKET_NAME`. Railway exposes `ACCESS_KEY_ID`, `SECRET_ACCESS_KEY`, `REGION`, and `ENDPOINT`, and supports passing them to another service with reference variables. [Railway Storage Buckets](https://docs.railway.com/storage-buckets), [Railway variables](https://docs.railway.com/variables)
- Railway bucket egress and S3 operations are free, but traffic from the application service to the bucket counts as service egress. Direct presigned GET/PUT flows avoid routing bytes through the service. [Railway Storage Buckets](https://docs.railway.com/storage-buckets), [Uploading & Serving Files](https://docs.railway.com/storage-buckets/uploading-serving)
- On Django 4.2+, `django-storages` is configured under `STORAGES["default"]`. Its S3 backend supports custom `endpoint_url`, `region_name`, `addressing_style`, private signed URLs (`querystring_auth=True`), expiration, and collision-safe names (`file_overwrite=False`). [django-storages S3 backend 1.14.6](https://django-storages.readthedocs.io/en/stable/backends/amazon-S3.html)
- Django's official multiple-upload pattern is a `ClearableFileInput` with `allow_multiple_selected=True`, a `FileField` that validates every item and always returns a list, and a view that handles each list item. One model file field still represents only one file. [Django file uploads](https://docs.djangoproject.com/en/5.2/topics/http/file-uploads/)
- A `FieldFile` may wrap a remote storage object. Application code should use `open()`, `read()`, `size`, and `url`; `path` is specifically a local-filesystem path delegated to the backend and is not portable to S3. [Django managing files](https://docs.djangoproject.com/en/5.1/topics/files/), [Django `FileField` / `FieldFile`](https://docs.djangoproject.com/en/5.1/ref/models/fields/#filefield)
- Django recommends upload-size limits and strict handling of untrusted user content. [Django user-uploaded content security](https://docs.djangoproject.com/en/5.2/topics/security/#user-uploaded-content)

## Current code inventory

### Storage and model fields

Production explicitly uses local filesystem media in `budo_database/settings/production.py:35-46`. The persistent fields that will follow the production `default` storage are:

- `Turnus.uploadedFile` — `budo_app/models.py:391-396`
- `AuslagerorteImage.image` — `budo_app/models.py:660-668`
- `Document.uploadedFile` (admin-only in the inspected code) — `budo_app/models.py:685-688`

Static files should remain unchanged on `whitenoise.storage.CompressedManifestStaticFilesStorage`.

The local checkout currently contains 46 ignored files (386,061 bytes), all under `media/Uploaded Files/`, and no local `auslagerorte_images/` files. The database configured in this working environment currently reports two `Turnus` rows with files, no `AuslagerorteImage` rows, and no `Document` rows. This is only an inventory clue, **not confirmation that this is the production dataset**. The mismatch also suggests old replacement uploads may be orphaned and should not automatically be copied without a retention decision.

### Existing URL generation

Both the legacy template and React data path already call the storage abstraction:

- `budo_app/templates/auslagerorte-detail.html:75-77`
- `budo_app/api_views.py:280-295`

After the backend switch, these calls will generate presigned Railway URLs. The default django-storages expiration is one hour. That is a reasonable initial value for this authenticated app, but an image left open longer than the URL lifetime can stop loading until app data is refreshed.

### Storage-incompatible code

`budo_app/excelProcessor.py:77-103` joins `MEDIA_ROOT` to a field name, checks `os.path.exists()`, and uses Python's filesystem `open()`. An S3 backend does not provide a local path, so Turnus imports will fail after a naive backend switch.

Refactor this flow to open the field through storage, conceptually:

```python
with turnus.uploadedFile.open("rb") as excel_file:
    budo = pd.read_excel(excel_file, sheet_name="DataCleaner", header=1)
    excel_file.seek(0)
    budo_raw = pd.read_excel(excel_file, sheet_name="RawData", header=0)
```

`budo_app/excel_views.py:92-110` also creates a generated download under `MEDIA_ROOT`. That export is temporary response data, not persisted user media. It should use a securely named temporary file (or an in-memory buffer where practical) rather than depending on media storage.

`django-resized` 1.0.3 is expected to work with remote storage: its installed `ResizedImageFieldFile.save()` transforms the uploaded image in memory and then delegates to the parent `FieldFile.save()`, which uses the configured storage. This still needs an integration test against a Railway bucket.

## Proposed production configuration

Add the S3 extra to production dependencies (currently neither `django-storages` nor `boto3` is installed):

```text
django-storages[s3]==1.14.6
```

Configure only production media storage:

```python
# budo_database/settings/production.py
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": os.environ["S3_BUCKET_NAME"],
            "access_key": os.environ["S3_ACCESS_KEY_ID"],
            "secret_key": os.environ["S3_SECRET_ACCESS_KEY"],
            "endpoint_url": os.environ["S3_ENDPOINT_URL"],
            "region_name": os.environ["S3_REGION_NAME"],
            "addressing_style": os.environ.get(
                "S3_ADDRESSING_STYLE", "virtual"
            ),
            "signature_version": "s3v4",
            "default_acl": None,
            "querystring_auth": True,
            "querystring_expire": 3600,
            "file_overwrite": False,
        },
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
```

Do not add an S3 `location` prefix during the initial migration. Preserving existing field names as exact object keys means the database does not need a data migration.

Validate all five required variables at settings startup and raise `ImproperlyConfigured` with variable names only—never credential values.

### Railway setup

1. Create a Bucket in the production Railway environment, preferably in the same region as the Django service. The region cannot be changed later.
2. In the Django service's Variables tab, create references using Railway autocomplete:

```text
S3_BUCKET_NAME=${{<bucket-service>.BUCKET}}
S3_ACCESS_KEY_ID=${{<bucket-service>.ACCESS_KEY_ID}}
S3_SECRET_ACCESS_KEY=${{<bucket-service>.SECRET_ACCESS_KEY}}
S3_REGION_NAME=${{<bucket-service>.REGION}}
S3_ENDPOINT_URL=${{<bucket-service>.ENDPOINT}}
S3_ADDRESSING_STYLE=virtual
```

3. Confirm the actual Credentials tab says `virtual`. Use `path` for a legacy bucket if Railway says it requires path style.
4. No bucket CORS configuration is required for the recommended first version because the browser uploads to Django, not directly to S3.

## Serving strategy

### Recommended now: Django upload + presigned bucket GET

- Browser uploads to the existing authenticated Django endpoint.
- Django validates and resizes each image, then `S3Storage` writes it to Railway.
- Templates and React receive signed `.url` values and the browser fetches images directly from Railway.

Advantages: minimal code change, preserves `django-resized`, private bucket, bucket serves downloads directly. Cost: Django-to-bucket writes count as service egress.

A backend proxy would provide stable application URLs and stricter per-request authorization but incurs service egress for every read. Direct browser PUT uploads are a possible later optimization for large files, but they would bypass the current synchronous resize/validation flow and require a finalize/processing design plus CORS.

Presigned URLs are bearer URLs: anyone who receives one can use it until expiry. Keep expiry bounded and avoid logging full signed URLs.

## Upload form audit

| Upload | Multi-file status | Findings |
|---|---|---|
| Location images | **Selection and transport work** | The HTML form has multipart encoding; React sets `multiple`; `FormData(form)` preserves repeated file entries; the Django widget/form/view follow the official multi-file shape. |
| Turnus workbook | Correctly single-file | One workbook belongs to one Turnus. Must be refactored away from local paths before S3. No extension/size validation. |
| Spezialfamilien workbook | Correctly single-file | It is called `CSVUploadForm`/`csv_file`, but the UI says XLSX and the view calls `pandas.read_excel`. No extension/size validation. |
| `Document` admin upload | Single-file per model row | There is no custom bulk form. Supporting document bulk upload would require one `Document` row per file and a separate multi-file form/view. |

### Location image issues to fix

1. **Not actually image-validated.** `MultipleFileField` subclasses `forms.FileField`, not `forms.ImageField`. Because the view manually calls `objects.create()` and model `save()` does not run `full_clean()`, arbitrary bytes pass form validation and then may crash inside Pillow. A local probe confirmed two fake “image” files made the form valid.
2. **Empty upload succeeds.** `required=False` accepts no files and the view reports “Bilder hochgeladen!”. A local probe confirmed an empty form is valid and cleans to `[]`.
3. **Inconsistent clean return type.** The non-list branch returns a single file rather than the list required by the official Django pattern. Normal multipart use of this widget returns a list even for one file, but the field contract should still always be a list.
4. **No limits.** Add a configurable maximum file count, per-file byte limit, aggregate request limit, and decoded pixel/dimension limit. Validate every file before writing any object. Exact limits are a product/operations decision.
5. **Partial failure.** If image 3 fails after images 1 and 2 were written, the current loop can leave a partial batch and return a server error. Validate the full batch first, then either define partial success explicitly or clean up records/objects created by a failed batch. A database transaction alone cannot roll back S3 writes.
6. **Metadata privacy.** `ResizedImageField` forces JPEG but currently keeps metadata by default. Set `keep_meta=False` if GPS/EXIF metadata should not be retained.
7. **Input UX.** Add `accept="image/*"` as a picker hint, while retaining server validation.
8. **No regression coverage.** Add tests for two valid images creating two rows/objects, one valid image, empty upload rejection, invalid image rejection, configured count/size limits, batch cleanup, and the React `multiple` input.

The current implementation otherwise uses the correct one-row-per-image model shape: multiple selected files become multiple `AuslagerorteImage` rows.

## Object lifecycle

Django does not automatically delete stored bytes when a model row is deleted. Current cascade deletion of `AuslagerorteImage` rows and replacement of Turnus workbooks can therefore leave S3 objects behind. Add an explicit, transaction-aware cleanup policy and a periodic orphan-audit command. Do not blindly delete every unreferenced object until retention requirements for old workbooks are decided.

## Existing-file migration and safe rollout

Changing `STORAGES` affects future reads/writes immediately but does not copy existing bytes. Database fields contain storage-relative names, so preserve each name as the destination object key.

1. **Inventory before deployment:** export all non-empty names from the three model fields; compare them with all local media files; classify referenced, missing, and orphaned files.
2. **Confirm the source:** Railway deployment filesystems are not durable object storage. Determine whether the authoritative existing bytes are still in the running production container, a mounted volume, this local media directory, or a backup. Do not redeploy the current container until this is known if it may be the only copy.
3. **Create a staging bucket/environment:** Railway environments receive isolated bucket instances and credentials.
4. **Refactor and test storage-neutral code:** especially the workbook importer and its path-dependent test at `budo_app/tests.py:200`.
5. **Copy referenced objects preserving exact names:** make the operation idempotent; skip only after checking destination size/content, and emit a machine-readable report.
6. **Verify:** every referenced key exists, sizes match, sample images decode, sample workbooks import, signed URLs return the expected content type, and delete/replace behavior is known.
7. **Switch production default storage.** Keep staticfiles on WhiteNoise.
8. **Smoke test:** upload two images, display them, upload/process a workbook, replace/delete test media, and inspect Railway logs without printing signed URLs or secrets.
9. **Reconcile after cutover:** rerun the referenced-key audit before applying any orphan retention/deletion policy.

If the old bytes exist only inside the currently running Railway service, migration needs a one-off extraction/copy plan that runs while that deployment is still available. A normal code deployment may replace the container and lose that source.

## Validation performed during this research

- Backend test suite: 30 tests passed using a temporary SQLite test database.
- Frontend test suite: 26 tests passed.
- Django production deploy check completed; the only warning was expected because a short dummy secret was supplied to the check.
- Direct form probe: two invalid fake images were accepted; empty image selection was accepted.
- No live Railway bucket was created or mutated, and no S3 integration test was run because credentials were not available.

## Related risk outside the storage change

The project pins Django 5.1.3. Django's own documentation now marks the 5.1 line unsupported/insecure. Plan an upgrade to a supported release (preferably the 5.2 LTS line) separately or as a prerequisite security commit; it is not technically required for `django-storages`.

## Decisions needed before implementation

1. Maximum image count, bytes per image, aggregate upload bytes, and decoded dimensions/pixels.
2. Whether image EXIF/GPS metadata must be stripped (recommended: yes).
3. Whether a failed multi-image batch is all-or-nothing (recommended) or may partially succeed.
4. Presigned URL lifetime (one hour is the django-storages default).
5. Whether the admin `Document` model also needs a user-facing bulk upload flow.
6. Retention policy for replaced/unreferenced workbook and media objects.
7. Location of the authoritative existing production media bytes.
