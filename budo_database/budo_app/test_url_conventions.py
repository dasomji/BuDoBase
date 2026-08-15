from django.test import SimpleTestCase
from django.urls import Resolver404, resolve, reverse


class PageUrlConventionTests(SimpleTestCase):
    legacy_slashless_pages = (
        ("kids_list", (), "/all_kids"),
        ("zugabreise", (), "/zugabreise"),
        ("zuganreise", (), "/zuganreise"),
        ("kid_details", (21,), "/kid_details/21"),
        ("kid-edit-page", (21,), "/kid_details/21/edit"),
        ("check_in", (21,), "/check_in/21"),
        ("check_out", (21,), "/check_out/21"),
        ("serienbrief", (), "/serienbrief"),
        ("murdergame", (), "/murdergame"),
        ("schwerpunkt-create", (), "/schwerpunkt/create"),
        ("schwerpunkt-update", (21,), "/schwerpunkt/21/update"),
        ("swpmeals", (21,), "/swpmeals/21"),
        ("auslagerorte-create", (), "/auslagerorte/create"),
        ("auslagerorte-update", (21,), "/auslagerorte/21/update"),
        ("kitchen", (), "/kitchen"),
        ("swp-einteilung-w1", (), "/swp-einteilung-w1"),
        ("swp-einteilung-w2", (), "/swp-einteilung-w2"),
    )

    def test_static_page_resolves_with_and_without_trailing_slash(self):
        slashless_match = resolve("/all_kids")
        slash_match = resolve("/all_kids/")

        self.assertIs(slash_match.func, slashless_match.func)

    def test_parameterized_page_resolves_with_and_without_trailing_slash(self):
        slashless_match = resolve("/kid_details/21")
        slash_match = resolve("/kid_details/21/")

        self.assertIs(slash_match.func, slashless_match.func)
        self.assertEqual(slash_match.kwargs, {"id": 21})
        self.assertEqual(slashless_match.kwargs, {"id": 21})

    def test_retired_swp_dashboard_no_longer_resolves(self):
        for path in ("/swp-dashboard", "/swp-dashboard/"):
            with self.subTest(path=path), self.assertRaises(Resolver404):
                resolve(path)

    def test_every_legacy_page_keeps_exact_slashless_resolution(self):
        for name, args, slashless_url in self.legacy_slashless_pages:
            with self.subTest(name=name):
                slashless_match = resolve(slashless_url)
                slash_match = resolve(f"{slashless_url}/")

                self.assertIs(slash_match.func, slashless_match.func)
                self.assertEqual(reverse(name, args=args), slashless_url)
