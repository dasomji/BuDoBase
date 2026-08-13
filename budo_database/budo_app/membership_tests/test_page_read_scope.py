from datetime import date
from threading import Event, Thread
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import close_old_connections
from django.http import HttpResponse
from django.test import Client, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse

from budo_app.memberships import create_membership, select_turnus
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
