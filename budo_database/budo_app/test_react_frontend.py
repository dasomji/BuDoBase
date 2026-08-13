from datetime import date
from pathlib import Path

from django.contrib.auth.models import Permission, User
from django.http import HttpResponse
from django.contrib.staticfiles import finders
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.test import TestCase, override_settings
from django.urls import path, reverse

from .api_views import submit_form
from .forms import GeldForm
from .models import (
    Auslagerorte,
    Geld,
    HappyCleaning,
    Kinder,
    Schwerpunkte,
    Turnus,
)


def unstructured_form_response(request):
    return HttpResponse("<html><body>Validation failed.</body></html>")


urlpatterns = [
    path("api/form-submit/", submit_form, name="unstructured-form-submit-api"),
    path("login/", unstructured_form_response),
]


class ReactShellTests(TestCase):
    def test_request_renders_the_react_shell_once(self):
        response = self.client.get(reverse("login"))

        rendered_templates = [
            template.name
            for template in response.templates
        ]
        self.assertEqual(rendered_templates.count("react_app.html"), 1)

    def test_frontend_chunks_do_not_reimport_the_executable_entry_bundle(self):
        project_root = Path(__file__).resolve().parent.parent
        asset_directory = project_root / "budo_app/static/frontend/assets"
        offending_chunks = [
            path.name
            for path in asset_directory.glob("*.js")
            if 'from"../app.js"' in path.read_text()
            or "from'../app.js'" in path.read_text()
        ]

        self.assertEqual(
            offending_chunks,
            [],
            "Production-hashed app.js must not be reimported through its "
            "unhashed URL; that executes a second React root.",
        )

    def test_design_system_bundle_has_no_legacy_stylesheet_or_cascade_layer(self):
        project_root = Path(__file__).resolve().parent.parent
        source = (project_root / "frontend/src/app.css").read_text()
        frontend_sources = "\n".join(
            path.read_text()
            for suffix in ("*.js", "*.jsx", "*.css")
            for path in (project_root / "frontend/src").rglob(suffix)
        )
        built_css = (project_root / "budo_app/static/frontend/app.css").read_text()

        self.assertNotIn("stylesheet.css", source)
        self.assertNotIn("layer(legacy)", source)
        self.assertNotRegex(source, r"@layer[^;{]*\blegacy\b")
        self.assertIsNone(finders.find("stylesheet.css"))
        self.assertNotIn("display: grid !important", source)
        self.assertNotIn("display: flex !important", source)
        self.assertNotIn("width: max-content !important", source)
        self.assertNotIn("Layered !important declarations", source)
        self.assertNotRegex(
            source,
            r"@media[^{]*(?:600|640|760|761|768|1024)px",
        )
        self.assertNotRegex(
            frontend_sources,
            r"(?:^|[:\s\"'])(?:sm|md|lg|xl|2xl):(?=[a-z[])",
        )
        self.assertNotRegex(
            frontend_sources,
            r"(?:min|max)-\[(?!(?:900|901)px)\d+px\]:",
        )
        self.assertNotRegex(
            built_css,
            r"@media[^{]*(?:width\s*[<>]=?\s*(?:40rem|48rem)|"
            r"(?:600|640|768|1024)px)",
        )

    def test_named_legacy_ui_assets_are_removed_after_their_references(self):
        project_root = Path(__file__).resolve().parent.parent
        legacy_static = (
            "js/csrf.js",
            "js/filtertable.js",
            "js/image-gallery.js",
            "js/map.js",
            "js/swp-choice.js",
            "js/card_functionality.js",
            "js/edit-freunde.js",
            "js/edit-notiz.js",
            "js/header.js",
            "js/pfand-controls.js",
            "js/zugabreise-toggle.js",
            "js/zuganreise-toggle.js",
        )
        legacy_templates = (
            "auslagerorte-detail.html",
            "auslagerorte-form.html",
            "auslagerorte-image-upload.html",
            "auslagerorte-list.html",
            "budo_familien.html",
            "check_in.html",
            "check_in_kid.html",
            "check_out.html",
            "components/card.html",
            "components/interactionbar.html",
            "components/ja_nein_switch.html",
            "components/map.html",
            "components/mapheader.html",
            "components/openicon.html",
            "components/pin_overlay.html",
            "components/swp_table.html",
            "filter-table.html",
            "filter_search.html",
            "kids_data.html",
            "kids_list.html",
            "kindergeburtstage.html",
            "kindergesamtzahl.html",
            "kitchen.html",
            "main.html",
            "master.html",
            "murdergame.html",
            "navbar.html",
            "schwerpunkt-detail.html",
            "schwerpunkt-form.html",
            "serienbrief.html",
            "spezial_familien.html",
            "swp-dashboard.html",
            "swp-einteilung.html",
            "swpmeals.html",
            "upload-file.html",
            "upload_excel.html",
            "uploadspezialfamilien.html",
            "users/already_registered.html",
            "users/dashboard.html",
            "users/login.html",
            "users/profil.html",
            "users/register.html",
            "users/team.html",
            "zugabreise.html",
            "zuganreise.html",
        )
        template_sources = "\n".join(
            path.read_text()
            for template_root in (
                project_root / "budo_app/templates",
                project_root / "users/templates",
            )
            for path in template_root.rglob("*.html")
        )

        for asset in legacy_static:
            self.assertIsNone(finders.find(asset), asset)
            self.assertNotIn(asset, template_sources)
        for template_name in legacy_templates:
            with self.assertRaises(TemplateDoesNotExist, msg=template_name):
                get_template(template_name)
            self.assertNotIn(template_name, template_sources)
        self.assertNotIn('id="mySidebar"', template_sources)
        self.assertNotIn('class="number-pad"', template_sources)
        self.assertNotIn('class="pfand-controls"', template_sources)
        self.assertNotIn('class="modal"', template_sources)
        self.assertEqual(
            [
                path.relative_to(project_root).as_posix()
                for template_root in (
                    project_root / "budo_app/templates",
                    project_root / "users/templates",
                )
                for path in template_root.rglob("*.html")
            ],
            ["budo_app/templates/react_app.html"],
        )

    def test_deploy_collects_static_and_generated_directory_is_ignored(self):
        project_root = Path(__file__).resolve().parent.parent
        railway = (project_root / "railway.json").read_text()
        gitignore = (project_root / ".gitignore").read_text().splitlines()
        agent_guide = (project_root / "AGENTS.md").read_text()

        self.assertIn("python manage.py collectstatic --noinput", railway)
        self.assertIn("staticfiles/", gitignore)
        self.assertIn(
            "python manage.py collectstatic --clear --noinput",
            agent_guide,
        )

    def test_template_page_uses_the_react_mount_for_screen_and_print(self):
        response = self.client.get(reverse("login"))

        self.assertContains(response, '<div id="root"></div>', html=True)
        self.assertContains(response, "/static/frontend/app.js")
        self.assertContains(
            response,
            'id="react-app-styles" rel="stylesheet" '
            'href="/static/frontend/app.css" media="all"',
        )
        self.assertNotContains(response, 'id="legacy-print-root"')
        self.assertNotContains(response, "bootstrap@5.3.0")
        self.assertNotContains(response, 'href="/static/stylesheet.css"')
        self.assertNotContains(response, "data-react-print-page")
        self.assertNotContains(response, "fonts.googleapis.com")
        self.assertNotContains(response, "fonts.gstatic.com")

    def test_team_page_deep_link_uses_the_authenticated_react_shell(self):
        user = User.objects.create_user("team-page-user", password="secret")
        self.client.force_login(user)

        response = self.client.get(reverse("team"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<div id="root"></div>', html=True)
        self.assertContains(response, "/static/frontend/app.js")

    def test_team_page_deep_link_requires_authentication(self):
        response = self.client.get("/team/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/login/?next=/team/")

    def test_kitchen_uses_the_same_react_shell_as_every_other_page(self):
        user = User.objects.create_user("kitchen-print-user", password="secret")
        self.client.force_login(user)

        response = self.client.get(reverse("kitchen"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'id="react-app-styles" rel="stylesheet" '
            'href="/static/frontend/app.css" media="all"',
        )
        self.assertNotContains(response, "data-react-print-page")
        self.assertNotContains(response, "legacy-print-root")

    def test_own_profile_view_and_edit_deep_links_are_separate_and_protected(self):
        user = User.objects.create_user("own-profile-routes", password="secret")
        detail_url = reverse("profil")
        edit_url = reverse("profil-edit")

        for url in (detail_url, edit_url):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, f"/login/?next={url}")

        self.client.force_login(user)
        self.assertEqual(self.client.get(detail_url).status_code, 200)
        self.assertEqual(self.client.get(edit_url).status_code, 200)
        self.assertEqual(self.client.post(detail_url).status_code, 405)

    def test_selected_profile_edit_deep_link_requires_profile_permission(self):
        editor = User.objects.create_user("profile-editor", password="secret")
        selected = User.objects.create_user("selected-profile").profil
        url = reverse("profil-admin", args=(selected.id,))
        self.client.force_login(editor)

        denied = self.client.get(url)
        editor.user_permissions.add(
            Permission.objects.get(codename="change_profil"),
        )
        allowed = self.client.get(url)

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(allowed.status_code, 200)
        self.assertContains(allowed, '<div id="root"></div>', html=True)

    def test_selected_profile_edit_deep_link_requires_authentication(self):
        selected = User.objects.create_user("selected-profile-login").profil
        url = reverse("profil-admin", args=(selected.id,))

        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/login/?next={url}")

    def test_api_response_is_not_replaced(self):
        response = self.client.get(reverse("bootstrap-api"))

        self.assertEqual(response["Content-Type"], "application/json")

    def test_invalid_html_form_response_stays_in_react(self):
        response = self.client.post(
            reverse("login"),
            {"username": "missing", "password": "incorrect"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<div id="root"></div>', html=True)


class ReactPageRouteSmokeTests(TestCase):
    non_page_route_names = {
        "attachment-media",
        "download_updated_excel",
        "place-delete-api",
        "place-image-delete-api",
        "place-tag-create-api",
        "place-tag-update-api",
        "place-tag-delete-api",
        "recalculate-travel-times-api",
        "turnus-join-request-api",
        "logout",
        "toggle_zug_abreise",
        "admin-membership-role-api",
        "update_birthdays_from_sv",
        "update_freunde",
        "update_notiz_abreise",
        "update_pfand",
        "update_schwerpunkt_wahl",
    }

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            "route-smoke-user",
            "route-smoke@example.test",
            "secret",
        )
        cls.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        cls.user.profil.turnus = cls.turnus
        cls.user.profil.save(update_fields=["turnus"])
        cls.place = Auslagerorte.objects.create(
            name="Route smoke place",
            koordinaten="48.5, 15.0",
        )
        cls.focus = Schwerpunkte.objects.create(
            swp_name="Route smoke focus",
            schwerpunktzeit=cls.turnus.schwerpunktzeit_set.get(woche="w1"),
            ort=cls.place,
        )
        cls.kid = Kinder.objects.create(
            kid_index="SMOKE-1",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            kid_birthday=date(2012, 7, 2),
            turnus=cls.turnus,
            anmelder_vorname="Ann",
            anmelder_nachname="Lovelace",
            rechnungsadresse="Main street",
            rechnung_ort="Vienna",
            rechnung_land="Austria",
        )
        cls.event = HappyCleaning.objects.create(
            turnus=cls.turnus,
            display_number=1,
        )

    def test_every_registered_browser_page_route_renders_the_react_shell(self):
        from budo_app.urls import urlpatterns as budo_urlpatterns
        from users.urls import urlpatterns as user_urlpatterns

        route_urls = {
            "uploadFile": reverse("uploadFile"),
            "upload_excel": reverse("upload_excel", args=(self.turnus.id,)),
            "kids_list": reverse("kids_list"),
            "zugabreise": reverse("zugabreise"),
            "zuganreise": reverse("zuganreise"),
            "kid_details": reverse("kid_details", args=(self.kid.id,)),
            "kid-edit-page": reverse("kid-edit-page", args=(self.kid.id,)),
            "check_in": reverse("check_in", args=(self.kid.id,)),
            "check_out": reverse("check_out", args=(self.kid.id,)),
            "serienbrief": reverse("serienbrief"),
            "murdergame": reverse("murdergame"),
            "schwerpunkt-create": reverse("schwerpunkt-create"),
            "schwerpunkt-detail": reverse(
                "schwerpunkt-detail",
                args=(self.focus.id,),
            ),
            "schwerpunkt-update": reverse(
                "schwerpunkt-update",
                args=(self.focus.id,),
            ),
            "swpmeals": reverse("swpmeals", args=(self.focus.id,)),
            "swp-dashboard": reverse("swp-dashboard"),
            "auslagerorte-list": reverse("auslagerorte-list"),
            "place-tag-settings": reverse("place-tag-settings"),
            "admin-settings-page": reverse("admin-settings-page"),
            "auslagerorte-create": reverse("auslagerorte-create"),
            "auslagerorte-detail": reverse(
                "auslagerorte-detail",
                args=(self.place.id,),
            ),
            "auslagerorte-update": reverse(
                "auslagerorte-update",
                args=(self.place.id,),
            ),
            "auslagerorte-image-upload": reverse(
                "auslagerorte-image-upload",
                args=(self.place.id,),
            ),
            "kitchen": reverse("kitchen"),
            "swp-einteilung-w1": reverse("swp-einteilung-w1"),
            "swp-einteilung-w2": reverse("swp-einteilung-w2"),
            "happy-cleaning-assignment-page": reverse(
                "happy-cleaning-assignment-page",
                args=(self.event.id,),
            ),
            "happy-cleaning-print-page": reverse(
                "happy-cleaning-print-page",
            ),
            "happy-cleaning-event-print-page": reverse(
                "happy-cleaning-event-print-page",
                args=(self.event.id,),
            ),
            "happy_cleaning": reverse("happy_cleaning"),
            "kindergesamtzahl": reverse("kindergesamtzahl"),
            "budo_familien": reverse("budo_familien"),
            "upload_spezialfamilien": reverse("upload_spezialfamilien"),
            "spezial_familien": reverse("spezial_familien"),
            "kindergeburtstage": reverse("kindergeburtstage"),
            "team": reverse("team"),
            "dashboard": reverse("dashboard"),
            "good-to-know": reverse("good-to-know"),
            "register": reverse("register"),
            "profil": reverse("profil"),
            "profil-edit": reverse("profil-edit"),
            "profil-admin": reverse("profil-admin", args=(self.user.profil.id,)),
        }
        registered_page_names = {
            pattern.name
            for pattern in (*budo_urlpatterns, *user_urlpatterns)
            if pattern.name and pattern.name not in self.non_page_route_names
        }

        self.assertEqual(registered_page_names, route_urls.keys() | {"login"})

        login_response = self.client.get(reverse("login"))
        self.assertEqual(login_response.status_code, 200)
        self.assertContains(login_response, '<div id="root"></div>', html=True)

        self.client.force_login(self.user)
        route_urls["dashboard-root"] = "/"
        for route_name, url in route_urls.items():
            with self.subTest(route=route_name, url=url):
                response = self.client.get(url, follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertContains(
                    response,
                    '<div id="root"></div>',
                    html=True,
                )
                self.assertContains(response, "/static/frontend/app.js")


class FormSubmitApiTests(TestCase):
    @override_settings(ROOT_URLCONF=__name__)
    def test_unstructured_form_errors_fail_loudly(self):
        with self.assertRaisesMessage(
            RuntimeError,
            "did not provide structured form errors",
        ):
            self.client.post(
                reverse("unstructured-form-submit-api"),
                {"_target": "/login/"},
            )

    def test_login_validation_is_returned_as_json(self):
        response = self.client.post(
            reverse("form-submit-api"),
            {"_target": "/login/", "username": "missing", "password": "bad"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["ok"])
        self.assertIn(
            "Invalid username or password",
            response.json()["errors"],
        )
        self.assertEqual(
            self.client.get(reverse("bootstrap-api")).json()["messages"],
            [],
        )

    def test_login_success_returns_redirect_contract(self):
        User.objects.create_user("api-login", password="secret")

        response = self.client.post(
            reverse("form-submit-api"),
            {"_target": "/login/", "username": "api-login", "password": "secret"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertIn("redirect", response.json())


class PocketMoneyFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("money-user", password="secret")
        self.turnus = Turnus.objects.create(turnus_nr=3, turnus_beginn=date(2026, 7, 1))
        self.user.profil.turnus = self.turnus
        self.user.profil.save()
        self.kid = Kinder.objects.create(
            kid_index="T3-1",
            kid_vorname="Ada",
            kid_nachname="Lovelace",
            kid_birthday=date(2012, 7, 2),
            turnus=self.turnus,
            anmelder_vorname="Ann",
            anmelder_nachname="Lovelace",
            rechnungsadresse="Main street",
            rechnung_ort="Vienna",
            rechnung_land="Austria",
        )
        self.client.force_login(self.user)

    def test_pocket_money_form_rejects_negative_input(self):
        self.assertFalse(GeldForm({"amount": -5}).is_valid())

    def test_kid_detail_buttons_apply_the_transaction_sign(self):
        for action, expected in (("withdraw", -5), ("topup", 5)):
            response = self.client.post(
                reverse("form-submit-api"),
                {"_target": f"/kid_details/{self.kid.id}", "amount": 5, "money_action": action},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(Geld.objects.latest("id").amount, expected)

    def test_checkout_subtracts_returned_money_from_a_positive_balance(self):
        Geld.objects.create(kinder=self.kid, added_by=self.user, amount=12.5)

        response = self.client.post(
            reverse("form-submit-api"),
            {"_target": f"/check_out/{self.kid.id}", "early_abreise_date": "2026-07-02", "amount": 12.5},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.kid.get_taschengeld_sum(), 0)

    def test_checkout_adds_money_paid_toward_a_negative_balance(self):
        Geld.objects.create(kinder=self.kid, added_by=self.user, amount=-3)

        response = self.client.post(
            reverse("form-submit-api"),
            {"_target": f"/check_out/{self.kid.id}", "early_abreise_date": "2026-07-02", "amount": 2},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.kid.get_taschengeld_sum(), -1)

    def test_checkout_uses_pfand_adjusted_balance_for_transaction_sign(self):
        self.kid.pfand = 1
        self.kid.save()
        Geld.objects.create(kinder=self.kid, added_by=self.user, amount=0.1)

        response = self.client.post(
            reverse("form-submit-api"),
            {"_target": f"/check_out/{self.kid.id}", "early_abreise_date": "2026-07-02", "amount": 0.15},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.kid.get_remaining_taschengeld(), 0)

    def test_checkout_rejects_a_negative_amount_without_checking_out(self):
        self.kid.anwesend = True
        self.kid.save()

        response = self.client.post(
            reverse("form-submit-api"),
            {"_target": f"/check_out/{self.kid.id}", "early_abreise_date": "2026-07-02", "amount": -2},
        )

        self.assertEqual(response.status_code, 422)
        self.kid.refresh_from_db()
        self.assertTrue(self.kid.anwesend)
