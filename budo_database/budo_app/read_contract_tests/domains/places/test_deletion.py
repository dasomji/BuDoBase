from datetime import date

from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from budo_app.memberships import create_membership, select_turnus
from budo_app.models import Auslagerorte, AuslagerorteImage, AuslagerorteNotizen, Turnus
from budo_app.read_contract_tests.fixtures import image_upload


TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=TEST_STORAGES)
class PlaceDeletionTests(TestCase):
    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user("place-deleter")
        self.user.profil.turnus = self.turnus
        self.user.profil.save(update_fields=["turnus"])
        create_membership(user=self.user, turnus=self.turnus)
        select_turnus(self.user, self.turnus)
        self.client.force_login(self.user)
        self.place = Auslagerorte.objects.create(name="Ada Hütte")

    def grant(self, codename):
        self.user.user_permissions.add(Permission.objects.get(codename=codename))
        self.user = User.objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    def test_place_delete_requires_permission_and_exact_server_side_name(self):
        url = reverse("place-delete-api", args=(self.place.id,))

        denied = self.client.post(url, {"confirmation_name": "Ada Hütte"}, content_type="application/json")
        self.grant("delete_auslagerorte")
        wrong_name = self.client.post(url, {"confirmation_name": "ada hütte"}, content_type="application/json")
        accepted = self.client.post(url, {"confirmation_name": "Ada Hütte"}, content_type="application/json")

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(wrong_name.status_code, 400)
        self.assertEqual(wrong_name.json()["code"], "confirmation_mismatch")
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.json()["deleted"], {"id": self.place.id, "name": "Ada Hütte"})
        self.assertFalse(Auslagerorte.objects.filter(pk=self.place.id).exists())

    def test_place_delete_cascades_notes_images_and_storage_object(self):
        self.grant("delete_auslagerorte")
        note = AuslagerorteNotizen.objects.create(
            auslagerort=self.place,
            notiz="Kommentar",
            added_by=self.user,
        )
        image = AuslagerorteImage.objects.create(
            auslagerort=self.place,
            notiz=note,
            image=image_upload("comment.png"),
        )
        storage = image.image.storage
        stored_name = image.image.name

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("place-delete-api", args=(self.place.id,)),
                {"confirmation_name": "Ada Hütte"},
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(storage.exists(stored_name))
        self.assertFalse(AuslagerorteNotizen.objects.filter(pk=note.id).exists())
        self.assertFalse(AuslagerorteImage.objects.filter(pk=image.id).exists())

    def test_image_delete_requires_its_permission_and_place_ownership(self):
        image = AuslagerorteImage.objects.create(
            auslagerort=self.place,
            image=image_upload("place.png"),
        )
        other_place = Auslagerorte.objects.create(name="Andere Hütte")
        url = reverse("place-image-delete-api", args=(self.place.id, image.id))

        denied = self.client.post(url, {}, content_type="application/json")
        self.grant("delete_auslagerorteimage")
        wrong_place = self.client.post(
            reverse("place-image-delete-api", args=(other_place.id, image.id)),
            {},
            content_type="application/json",
        )
        storage = image.image.storage
        stored_name = image.image.name
        with self.captureOnCommitCallbacks(execute=True):
            accepted = self.client.post(url, {}, content_type="application/json")

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(wrong_place.status_code, 404)
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.json()["deleted"]["id"], image.id)
        self.assertFalse(AuslagerorteImage.objects.filter(pk=image.id).exists())
        self.assertFalse(storage.exists(stored_name))

    def test_mutation_endpoints_require_authentication_and_csrf(self):
        image = AuslagerorteImage.objects.create(
            auslagerort=self.place,
            image=image_upload("place.png"),
        )
        place_url = reverse("place-delete-api", args=(self.place.id,))
        image_url = reverse("place-image-delete-api", args=(self.place.id, image.id))
        anonymous = Client()
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)

        for response in (
            anonymous.post(place_url, {}, content_type="application/json"),
            anonymous.post(image_url, {}, content_type="application/json"),
            csrf_client.post(place_url, {}, content_type="application/json"),
            csrf_client.post(image_url, {}, content_type="application/json"),
        ):
            self.assertEqual(response.status_code, 403)
