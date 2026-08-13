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
from budo_app.models import HappyCleaning, Kinder, Turnus


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

    def test_kids_page_holds_membership_through_render(self):
        Kinder.objects.create(
            kid_index="page-race",
            kid_vorname="Still",
            kid_nachname="Authorized",
            turnus=self.turnus,
        )
        self.assert_read_finishes_before_membership_removal(
            url=reverse("spezial_familien"),
            render_target="budo_app.kids_views.render_react_page",
        )

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
