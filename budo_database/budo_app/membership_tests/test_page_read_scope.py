from datetime import date
from threading import Event, Thread
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import close_old_connections
from django.http import HttpResponse, StreamingHttpResponse
from django.template.response import TemplateResponse
from django.test import (
    Client,
    RequestFactory,
    TransactionTestCase,
    skipUnlessDBFeature,
)
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from budo_app.memberships import (
    create_membership,
    membership_scoped_read,
    select_turnus,
)
from budo_app.models import (
    Auslagerorte,
    HappyCleaning,
    Kinder,
    Schwerpunkte,
    Turnus,
)


@skipUnlessDBFeature("has_select_for_update")
class PageReadMembershipScopeTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.turnus = Turnus.objects.create(
            turnus_nr=1,
            turnus_beginn=date(2026, 7, 1),
        )
        self.user = User.objects.create_user(username="page-reader")
        self.membership = create_membership(user=self.user, turnus=self.turnus)
        select_turnus(self.user, self.turnus)
        self.client.force_login(self.user)
        self.place = Auslagerorte.objects.create(name="Scoped place")
        self.focus = Schwerpunkte.objects.create(
            swp_name="Scoped focus",
            schwerpunktzeit=self.turnus.schwerpunktzeit_set.get(woche="w1"),
        )

    def update_urls(self):
        return (
            reverse("auslagerorte-update", args=(self.place.pk,)),
            reverse("schwerpunkt-update", args=(self.focus.pk,)),
        )

    def assert_read_finishes_before_membership_removal(self, *, url, render_target):
        reader_started = Event()
        allow_reader_to_finish = Event()
        deletion_finished = Event()
        result = {}

        def pause_render(*args, **kwargs):
            reader_started.set()
            self.assertTrue(allow_reader_to_finish.wait(5))
            return HttpResponse("authorized page")

        def read_page():
            close_old_connections()
            client = Client()
            client.force_login(User.objects.get(pk=self.user.pk))
            with patch(render_target, side_effect=pause_render):
                result["status"] = client.get(url).status_code
            close_old_connections()

        def remove_membership():
            close_old_connections()
            self.membership.__class__.objects.filter(pk=self.membership.pk).delete()
            deletion_finished.set()
            close_old_connections()

        reader = Thread(target=read_page)
        reader.start()
        self.assertTrue(reader_started.wait(5))
        remover = Thread(target=remove_membership)
        remover.start()
        self.assertFalse(deletion_finished.wait(0.2))
        allow_reader_to_finish.set()
        reader.join(5)
        remover.join(5)

        self.assertEqual(result["status"], 200)
        self.assertTrue(deletion_finished.is_set())

    def test_places_page_holds_membership_through_render(self):
        self.assert_read_finishes_before_membership_removal(
            url=reverse("auslagerorte-list"),
            render_target="budo_app.auslagerorte_views.render_react_page",
        )

    def test_happy_cleaning_page_holds_membership_through_render(self):
        event = HappyCleaning.objects.create(turnus=self.turnus, display_number=1)
        self.assert_read_finishes_before_membership_removal(
            url=reverse("happy-cleaning-assignment-page", args=(event.pk,)),
            render_target="budo_app.happy_cleaning_page_views.render_react_page",
        )

    def test_class_based_template_response_holds_membership_through_render(self):
        render_started = Event()
        allow_render_to_finish = Event()
        deletion_finished = Event()
        result = {}

        class PausingTemplateResponse(TemplateResponse):
            def render(self):
                render_started.set()
                self.assert_render_released = allow_render_to_finish.wait(5)
                return super().render()

        @method_decorator(membership_scoped_read, name="get")
        class DeferredPage(TemplateView):
            template_name = "react_app.html"

            def get_context_data(inner_self, **kwargs):
                return {
                    "kids": Kinder.objects.filter(
                        turnus=inner_self.request.active_turnus,
                    ),
                }

            def render_to_response(inner_self, context, **response_kwargs):
                return PausingTemplateResponse(
                    inner_self.request,
                    inner_self.template_name,
                    context,
                    **response_kwargs,
                )

        def read_page():
            close_old_connections()
            request = RequestFactory().get("/deferred-page/")
            request.user = User.objects.get(pk=self.user.pk)
            response = DeferredPage.as_view()(request)
            result["rendered"] = response.is_rendered
            result["released"] = response.assert_render_released
            close_old_connections()

        def remove_membership():
            close_old_connections()
            self.membership.__class__.objects.filter(pk=self.membership.pk).delete()
            deletion_finished.set()
            close_old_connections()

        reader = Thread(target=read_page)
        reader.start()
        self.assertTrue(render_started.wait(5))
        remover = Thread(target=remove_membership)
        remover.start()
        self.assertFalse(deletion_finished.wait(0.2))
        allow_render_to_finish.set()
        reader.join(5)
        remover.join(5)

        self.assertEqual(result, {"rendered": True, "released": True})
        self.assertTrue(deletion_finished.is_set())

    def test_head_is_scoped_and_renders_no_revoked_membership_data(self):
        Kinder.objects.create(
            kid_index="private-head",
            kid_vorname="Private",
            kid_nachname="Child",
            turnus=self.turnus,
        )
        self.membership.delete()

        @method_decorator(membership_scoped_read, name="get")
        class HeadPage(TemplateView):
            template_name = "react_app.html"

            def get_context_data(inner_self, **kwargs):
                active_turnus = inner_self.request.active_turnus
                return {
                    "kids": Kinder.objects.filter(turnus=active_turnus)
                    if active_turnus is not None
                    else Kinder.objects.none(),
                }

        request = RequestFactory().head("/head-page/")
        request.user = User.objects.get(pk=self.user.pk)
        response = HeadPage.as_view()(request)

        self.assertTrue(response.is_rendered)
        self.assertEqual(list(response.context_data["kids"]), [])
        self.assertNotIn(b"Private", response.content)

    def test_invalid_post_render_is_scoped_and_hides_revoked_membership_data(self):
        Kinder.objects.create(
            kid_index="private-invalid-post",
            kid_vorname="Private",
            kid_nachname="Invalid Post",
            turnus=self.turnus,
        )
        self.membership.delete()

        @method_decorator(membership_scoped_read, name="dispatch")
        class InvalidFormPage(TemplateView):
            template_name = "react_app.html"

            def post(inner_self, request, *args, **kwargs):
                return inner_self.render_to_response(
                    inner_self.get_context_data(form_errors=["required"]),
                )

            def get_context_data(inner_self, **kwargs):
                active_turnus = inner_self.request.active_turnus
                return {
                    **kwargs,
                    "kids": Kinder.objects.filter(turnus=active_turnus)
                    if active_turnus is not None
                    else Kinder.objects.none(),
                }

        request = RequestFactory().post("/invalid-form-page/", {})
        request.user = User.objects.get(pk=self.user.pk)
        response = InvalidFormPage.as_view()(request)

        self.assertTrue(response.is_rendered)
        self.assertEqual(response.context_data["form_errors"], ["required"])
        self.assertEqual(list(response.context_data["kids"]), [])
        self.assertNotIn(b"Private", response.content)

    def test_update_puts_have_active_turnus_for_valid_membership(self):
        kid = Kinder.objects.create(
            kid_index="private-valid-put",
            kid_vorname="Private",
            kid_nachname="Valid Put",
            turnus=self.turnus,
        )

        for url in self.update_urls():
            with self.subTest(url=url):
                response = self.client.put(
                    url,
                    data="",
                    content_type="application/x-www-form-urlencoded",
                )

                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.is_rendered)
                self.assertEqual(list(response.context_data["kids"]), [kid])

    def test_update_puts_hide_data_for_invalid_selected_turnus(self):
        Kinder.objects.create(
            kid_index="private-invalid-put",
            kid_vorname="Private",
            kid_nachname="Invalid Put",
            turnus=self.turnus,
        )
        unapproved_turnus = Turnus.objects.create(
            turnus_nr=2,
            turnus_beginn=date(2026, 8, 1),
        )
        self.user.profil.selected_turnus = unapproved_turnus
        self.user.profil.save()

        for url, expected_status in zip(self.update_urls(), (200, 404)):
            with self.subTest(url=url):
                response = self.client.put(
                    url,
                    data="",
                    content_type="application/x-www-form-urlencoded",
                )

                self.assertEqual(response.status_code, expected_status)
                if expected_status == 200:
                    self.assertTrue(response.is_rendered)
                    self.assertEqual(list(response.context_data["kids"]), [])
                self.assertNotIn(b"Private", response.content)

    def test_update_puts_hide_data_after_membership_revocation(self):
        Kinder.objects.create(
            kid_index="private-revoked-put",
            kid_vorname="Private",
            kid_nachname="Revoked Put",
            turnus=self.turnus,
        )
        self.membership.delete()

        for url, expected_status in zip(self.update_urls(), (200, 404)):
            with self.subTest(url=url):
                response = self.client.put(
                    url,
                    data="",
                    content_type="application/x-www-form-urlencoded",
                )

                self.assertEqual(response.status_code, expected_status)
                if expected_status == 200:
                    self.assertTrue(response.is_rendered)
                    self.assertEqual(list(response.context_data["kids"]), [])
                self.assertNotIn(b"Private", response.content)

    def test_update_pages_keep_patch_and_delete_disallowed(self):
        for url in self.update_urls():
            for method in (self.client.patch, self.client.delete):
                with self.subTest(url=url, method=method.__name__):
                    response = method(url)

                    self.assertEqual(response.status_code, 405)

    def test_streaming_response_is_not_eagerly_consumed(self):
        consumed = []

        @membership_scoped_read
        def streaming_page(request):
            def chunks():
                consumed.append(True)
                yield b"private stream"

            return StreamingHttpResponse(chunks())

        request = RequestFactory().get("/stream/")
        request.user = User.objects.get(pk=self.user.pk)
        response = streaming_page(request)

        self.assertTrue(response.streaming)
        self.assertEqual(consumed, [])
