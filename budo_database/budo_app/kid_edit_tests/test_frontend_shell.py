from django.contrib.auth.models import User
from django.test import TestCase


class KidEditFrontendShellTests(TestCase):
    url = "/kid_details/7/edit"

    def test_dedicated_edit_deep_link_requires_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/login/?next={self.url}")

    def test_authenticated_edit_deep_link_renders_the_react_shell(self):
        user = User.objects.create_user("kid-edit-shell", password="secret")
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<div id="root"></div>', html=True)
        self.assertContains(response, "/static/frontend/app.js")

    def test_edit_shell_is_read_only(self):
        user = User.objects.create_user("kid-edit-shell-method", password="secret")
        self.client.force_login(user)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 405)
