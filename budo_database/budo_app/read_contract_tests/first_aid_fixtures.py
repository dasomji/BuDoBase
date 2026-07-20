import hashlib
import uuid

from budo_app.first_aid_tests.fixtures import image_bytes, photo_model


def add_first_aid_photo(
    entry,
    storage,
    *,
    position,
    size=(32, 20),
    color=(32, 96, 160),
):
    """Persist a transformed-WebP-shaped photo for focused read tests."""
    payload = image_bytes("WEBP", size=size, color=color)
    key = f"{uuid.UUID(int=(entry.id << 16) + position + 1)}.webp"
    storage.save(key, content=_content_file(payload))

    model = photo_model()
    fields = {field.name for field in model._meta.concrete_fields}
    values = {
        "eintrag": entry,
        "datei": key,
        "position": position,
        "checksum": hashlib.sha256(payload).hexdigest(),
    }
    # Unit 02 may persist intrinsic dimensions instead of reopening protected
    # objects during every read. Support that schema once it exists.
    if "width" in fields:
        values["width"] = size[0]
    if "height" in fields:
        values["height"] = size[1]
    photo = model(**values)
    model.objects.bulk_create([photo])
    return photo


def _content_file(payload):
    from django.core.files.base import ContentFile

    return ContentFile(payload)
