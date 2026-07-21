from datetime import date
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.storage import InMemoryStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase
from django.urls import reverse
from PIL import Image

from budo_app.first_aid_photos import (
    create_first_aid_entry,
    create_note,
    process_first_aid_photos,
)
from budo_app.models import ErsteHilfeFoto, Kinder, NotizFoto, Turnus


def image_upload(image_format="PNG", size=(2400, 1200)):
    output = BytesIO()
    Image.new("RGB", size, (20, 80, 140)).save(output, format=image_format)
    extension = image_format.lower()
    return SimpleUploadedFile(
        f"iphone-photo.{extension}",
        output.getvalue(),
        content_type=f"image/{extension}",
    )


class EntryImageTests(TransactionTestCase):
    def setUp(self):
        self.storage = InMemoryStorage()
        self.fields = [
            NotizFoto._meta.get_field("datei"),
            ErsteHilfeFoto._meta.get_field("datei"),
        ]
        self.previous_storages = [field.storage for field in self.fields]
        for field in self.fields:
            field.storage = self.storage
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(username="entry-images")
        self.user.profil.turnus = self.turnus
        self.user.profil.save(update_fields=("turnus",))
        self.kid = Kinder.objects.create(
            kid_index="image-kid",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            turnus=self.turnus,
        )

    def tearDown(self):
        for field, storage in zip(self.fields, self.previous_storages):
            field.storage = storage

    def test_notes_and_first_aid_share_optimized_webp_images(self):
        processed = process_first_aid_photos([image_upload()])

        note = create_note(
            child=self.kid,
            actor=self.user,
            text="Sonnencreme",
            photos=processed,
        )
        first_aid = create_first_aid_entry(
            child=self.kid,
            actor=self.user,
            description="Knie gekühlt",
            photos=process_first_aid_photos([image_upload()]),
        )

        for photo in (note.fotos.get(), first_aid.fotos.get()):
            self.assertTrue(photo.datei.name.endswith(".webp"))
            self.assertLessEqual(max(photo.width, photo.height), 1600)
            with self.storage.open(photo.datei.name, "rb") as stored:
                with Image.open(stored) as image:
                    self.assertEqual(image.format, "WEBP")

        self.client.force_login(self.user)
        note_photo = note.fotos.get()
        response = self.client.get(
            reverse("attachment-media", args=("notes", note_photo.id))
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/webp")

    def test_admin_style_entry_delete_cascades_to_stored_images(self):
        note = create_note(
            child=self.kid,
            actor=self.user,
            text="Mit Foto",
            photos=process_first_aid_photos([image_upload()]),
        )
        storage_key = note.fotos.get().datei.name

        note.delete()

        self.assertFalse(self.storage.exists(storage_key))
