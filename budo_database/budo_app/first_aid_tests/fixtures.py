from contextlib import contextmanager
from io import BytesIO

from django.core.files.storage import InMemoryStorage
from PIL import Image

from budo_app.models import ErsteHilfeEintrag, ErsteHilfeFoto


class MemoryPhotoStorage(InMemoryStorage):
    pass


@contextmanager
def use_photo_storage(storage):
    field = ErsteHilfeFoto._meta.get_field("datei")
    previous = field.storage
    field.storage = storage
    try:
        yield storage
    finally:
        field.storage = previous


def image_bytes(image_format="WEBP", *, size=(32, 20), color=(32, 96, 160)):
    output = BytesIO()
    Image.new("RGB", size, color).save(output, format=image_format)
    return output.getvalue()


def photo_model():
    return ErsteHilfeFoto


def create_first_aid_entry_for_test(**values):
    return ErsteHilfeEintrag.objects.create(**values)


def bulk_create_first_aid_entries_for_test(entries):
    return ErsteHilfeEintrag.objects.bulk_create(entries)
