from datetime import date

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from budo_app.models import Kinder, Notizen, Turnus

from .test_entry_images import image_upload


def corrupt_upload():
    return SimpleUploadedFile(
        "kaputt.png", b"kein Bild", content_type="image/png"
    )


class NoteSubmissionTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(username="note-submission")
        self.user.profil.turnus = self.turnus
        self.user.profil.save(update_fields=("turnus",))
        self.kid = Kinder.objects.create(
            kid_index="note-kid",
            kid_vorname="Grace",
            kid_nachname="Hopper",
            turnus=self.turnus,
        )
        self.client.force_login(self.user)
        self.url = reverse("kid_details", args=(self.kid.id,))

    def test_rejected_note_photo_re_renders_with_error_instead_of_redirect(self):
        response = self.client.post(
            self.url,
            {"notiz": "Sonnencreme", "notiz_fotos": [corrupt_upload()]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "errorlist")
        self.assertFalse(Notizen.objects.exists())

    def test_rejected_note_photo_reports_failure_through_form_submit_api(self):
        response = self.client.post(
            reverse("form-submit-api"),
            {
                "_target": f"/kid_details/{self.kid.id}",
                "notiz": "Sonnencreme",
                "notiz_fotos": [corrupt_upload()],
            },
        )

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["errors"])
        self.assertFalse(Notizen.objects.exists())

    def test_photos_without_note_text_are_rejected(self):
        response = self.client.post(
            self.url,
            {"notiz": "", "notiz_fotos": [image_upload()]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bitte zu den Fotos eine Notiz eingeben.")
        self.assertFalse(Notizen.objects.exists())

    def test_geld_only_submission_still_redirects(self):
        response = self.client.post(self.url, {"amount": "5"})

        self.assertRedirects(
            response, self.url, fetch_redirect_response=False
        )
