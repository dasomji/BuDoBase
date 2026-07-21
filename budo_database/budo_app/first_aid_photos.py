import hashlib
import logging
import uuid
from dataclasses import dataclass
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

from .first_aid_contract import (
    FIRST_AID_DESCRIPTION_MAX_LENGTH,
    FIRST_AID_MAX_PHOTOS,
)
from .models import ErsteHilfeEintrag, ErsteHilfeFoto, Notizen, NotizFoto


logger = logging.getLogger(__name__)

# HEIC/HEIF decoding is opt-in in pillow-heif. Register it once at this
# application boundary before Pillow inspects any upload.
register_heif_opener()

SUPPORTED_FORMATS = frozenset({"JPEG", "PNG", "WEBP", "HEIF"})


class FirstAidPhotoError(ValidationError):
    pass


class FirstAidCreationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProcessedFirstAidPhoto:
    position: int
    storage_key: str
    content: bytes
    checksum: str
    width: int | None = None
    height: int | None = None

    def __post_init__(self):
        _validate_processed_photo(self)


def _is_opaque_webp_key(value):
    if not isinstance(value, str) or "/" in value or "\\" in value:
        return False
    if not value.endswith(".webp"):
        return False
    try:
        parsed = uuid.UUID(value[:-5])
    except (ValueError, AttributeError):
        return False
    return str(parsed) == value[:-5]


def _validate_processed_photo(photo):
    if (
        not isinstance(photo.position, int)
        or isinstance(photo.position, bool)
        or photo.position < 0
    ):
        raise ValueError("Image position must be a non-negative integer.")
    if not _is_opaque_webp_key(photo.storage_key):
        raise ValueError("Image storage key must be an opaque UUID WebP key.")
    if not isinstance(photo.content, bytes) or not photo.content:
        raise ValueError("EH photo content must be non-empty bytes.")
    expected_checksum = hashlib.sha256(photo.content).hexdigest()
    if photo.checksum != expected_checksum:
        raise ValueError("Image checksum does not match its transformed bytes.")
    if (
        not isinstance(photo.width, int)
        or isinstance(photo.width, bool)
        or photo.width < 1
        or not isinstance(photo.height, int)
        or isinstance(photo.height, bool)
        or photo.height < 1
    ):
        raise ValueError("Image dimensions must be positive integers.")


def _validated_creation_inputs(description, photos):
    if not isinstance(description, str) or not description.strip():
        raise ValueError("Entry text must not be blank.")
    if len(description) > FIRST_AID_DESCRIPTION_MAX_LENGTH:
        raise ValueError(
            f"Entry text must be at most {FIRST_AID_DESCRIPTION_MAX_LENGTH} characters."
        )
    photos = tuple(photos)
    if len(photos) > FIRST_AID_MAX_PHOTOS:
        raise ValueError(f"An entry may contain at most {FIRST_AID_MAX_PHOTOS} images.")
    for expected_position, photo in enumerate(photos):
        if not isinstance(photo, ProcessedFirstAidPhoto):
            raise ValueError("Entry creation requires processed image data.")
        _validate_processed_photo(photo)
        if photo.position != expected_position:
            raise ValueError("Image positions must be contiguous and start at zero.")
    if len({photo.storage_key for photo in photos}) != len(photos):
        raise ValueError("Image storage keys must be unique.")
    return photos


def _is_declared_as_supported(upload):
    name = str(getattr(upload, "name", "")).casefold()
    content_type = str(getattr(upload, "content_type", "")).casefold()
    return (
        name.endswith((".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"))
        or content_type in {
            "image/jpeg",
            "image/png",
            "image/webp",
            "image/heic",
            "image/heif",
        }
    )


def _decode_error(upload):
    if _is_declared_as_supported(upload):
        return FirstAidPhotoError("Das Foto ist beschädigt und kann nicht gelesen werden.")
    return FirstAidPhotoError("Dieses Bildformat wird nicht unterstützt.")


def _check_dimensions(image):
    pixels = image.width * image.height
    maximum = settings.ATTACHMENT_IMAGE_MAX_PIXELS
    if pixels > maximum:
        raise FirstAidPhotoError(
            "Das Foto überschreitet die erlaubte Megapixel-Grenze."
        )


def _process_one(upload, position):
    if upload.size > settings.ATTACHMENT_IMAGE_MAX_FILE_SIZE:
        raise FirstAidPhotoError("Ein Foto darf höchstens 10 MB groß sein.")

    try:
        upload.seek(0)
        with Image.open(upload) as candidate:
            decoded_format = (candidate.format or "").upper()
            if decoded_format not in SUPPORTED_FORMATS:
                raise FirstAidPhotoError("Dieses Bildformat wird nicht unterstützt.")
            _check_dimensions(candidate)
            if getattr(candidate, "n_frames", 1) != 1:
                raise FirstAidPhotoError("Bitte nur ein Einzelbild pro Foto hochladen.")
            candidate.verify()

        # verify() invalidates the decoder state, so reopen and fully decode.
        upload.seek(0)
        with Image.open(upload) as source:
            _check_dimensions(source)
            if getattr(source, "n_frames", 1) != 1:
                raise FirstAidPhotoError("Bitte nur ein Einzelbild pro Foto hochladen.")
            source.load()
            transformed = ImageOps.exif_transpose(source)
            if transformed.mode not in {"RGB", "RGBA"}:
                transformed = transformed.convert(
                    "RGBA" if "transparency" in transformed.info else "RGB"
                )
            elif transformed is source:
                transformed = source.copy()

        max_edge = settings.ATTACHMENT_IMAGE_MAX_EDGE
        if max(transformed.size) > max_edge:
            transformed.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        width, height = transformed.size

        output = BytesIO()
        # Passing no EXIF/XMP/ICC data deliberately creates a metadata-free file.
        transformed.save(output, format="WEBP", quality=settings.ATTACHMENT_IMAGE_WEBP_QUALITY)
        transformed.close()
    except FirstAidPhotoError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise FirstAidPhotoError(
            "Das Bild ist für eine sichere Verarbeitung zu groß."
        ) from error
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
        raise _decode_error(upload) from error
    finally:
        try:
            upload.seek(0)
        except (AttributeError, OSError):
            pass

    content = output.getvalue()
    return ProcessedFirstAidPhoto(
        position=position,
        storage_key=f"{uuid.uuid4()}.webp",
        content=content,
        checksum=hashlib.sha256(content).hexdigest(),
        width=width,
        height=height,
    )


def process_first_aid_photos(uploads):
    uploads = list(uploads)
    if len(uploads) > settings.ATTACHMENT_IMAGE_MAX_FILES:
        raise FirstAidPhotoError("Es sind höchstens 5 Fotos erlaubt.")
    return tuple(_process_one(upload, position) for position, upload in enumerate(uploads))


def store_processed_photo(
    *,
    entry,
    processed,
    photo_model,
    storage,
    compensation_names,
):
    """Persist one processed photo while exposing every key for compensation."""
    _validate_processed_photo(processed)
    intended_name = processed.storage_key
    if storage.exists(intended_name):
        raise FileExistsError(f"Private EH photo already exists: {intended_name}")

    # Record the known key before save(): a remote backend can write
    # successfully and still raise while processing its response.
    compensation_names.append(intended_name)
    saved_name = storage.save(
        intended_name,
        ContentFile(processed.content),
    )
    if saved_name != intended_name:
        if isinstance(saved_name, str) and saved_name:
            compensation_names.append(saved_name)
        raise OSError("Private EH storage silently renamed an audited key.")

    photo = photo_model(
        eintrag=entry,
        datei=saved_name,
        position=processed.position,
        width=processed.width,
        height=processed.height,
        checksum=processed.checksum,
    )
    photo.save()
    return photo


def compensate_attachment_storage(storage, names, *, compensated=None):
    """Best-effort cleanup, remembering successful deletes across retries."""
    compensated = compensated if compensated is not None else set()
    for name in reversed(names):
        if name in compensated:
            continue
        try:
            storage.delete(name)
        except Exception:
            logger.exception("Could not remove partially stored attachment %s", name)
        else:
            compensated.add(name)
    return compensated


def _create_entry_with_photos(*, entry_model, photo_model, text_field, child, actor, text, photos):
    """Create a text entry and its transformed images as one logical operation."""
    compensation_names = []
    storage = photo_model._meta.get_field("datei").storage
    try:
        photos = _validated_creation_inputs(text, photos)
        with transaction.atomic():
            entry = entry_model.objects.create(
                kinder=child,
                added_by=actor,
                **{text_field: text},
            )
            for processed in photos:
                store_processed_photo(
                    entry=entry,
                    processed=processed,
                    photo_model=photo_model,
                    storage=storage,
                    compensation_names=compensation_names,
                )
            return entry
    except Exception as error:
        compensate_attachment_storage(storage, compensation_names)
        raise FirstAidCreationError("Eintrag konnte nicht gespeichert werden") from error


def create_first_aid_entry(*, child, actor, description, photos, request=None):
    return _create_entry_with_photos(
        entry_model=ErsteHilfeEintrag,
        photo_model=ErsteHilfeFoto,
        text_field="beschreibung",
        child=child,
        actor=actor,
        text=description,
        photos=photos,
    )


def create_note(*, child, actor, text, photos):
    return _create_entry_with_photos(
        entry_model=Notizen,
        photo_model=NotizFoto,
        text_field="notiz",
        child=child,
        actor=actor,
        text=text,
        photos=photos,
    )
