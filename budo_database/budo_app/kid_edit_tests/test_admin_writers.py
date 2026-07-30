from datetime import date, timedelta

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from budo_app.admin import KinderAdminForm
from budo_app.kid_edit_writes import ChildWriteScopeError
from budo_app.models import Kinder, Schwerpunkte, Schwerpunktzeit, Turnus


class AdminChildWriterTests(TestCase):
    """RED contract tests for the admin adoption of versioned child writes."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(
            username="admin-161-04",
            email="admin-161-04@example.test",
            password="synthetic-test-password",
        )
        cls.turnus = Turnus.objects.create(
            turnus_nr=16104,
            turnus_beginn=date(2026, 7, 1),
        )
        cls.foreign_turnus = Turnus.objects.create(
            turnus_nr=16105,
            turnus_beginn=date(2026, 8, 1),
        )
        cls.period_w1 = Schwerpunktzeit.objects.get(
            turnus=cls.turnus,
            woche="w1",
        )
        cls.period_w2 = Schwerpunktzeit.objects.get(
            turnus=cls.turnus,
            woche="w2",
        )
        cls.period_u = Schwerpunktzeit.objects.create(
            turnus=cls.turnus,
            woche="u",
            swp_beginn=cls.turnus.turnus_beginn + timedelta(days=2),
            dauer=1,
        )
        cls.foreign_period = Schwerpunktzeit.objects.get(
            turnus=cls.foreign_turnus,
            woche="w1",
        )
        cls.focus_w1 = Schwerpunkte.objects.create(
            swp_name="Synthetic week one",
            schwerpunktzeit=cls.period_w1,
        )
        cls.focus_w1_alternative = Schwerpunkte.objects.create(
            swp_name="Synthetic week one alternative",
            schwerpunktzeit=cls.period_w1,
        )
        cls.focus_w2 = Schwerpunkte.objects.create(
            swp_name="Synthetic week two",
            schwerpunktzeit=cls.period_w2,
        )
        cls.focus_u = Schwerpunkte.objects.create(
            swp_name="Synthetic unclear period",
            schwerpunktzeit=cls.period_u,
        )
        cls.foreign_focus = Schwerpunkte.objects.create(
            swp_name="Synthetic foreign focus",
            schwerpunktzeit=cls.foreign_period,
        )
        cls.nullable_period_focus = Schwerpunkte.objects.create(
            swp_name="Synthetic focus without period",
            schwerpunktzeit=None,
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.child = self._create_child("SYNTHETIC-ADMIN-161-04")
        self.child.schwerpunkte.add(
            self.focus_w1,
            self.focus_w2,
            self.focus_u,
            self.foreign_focus,
        )
        self.change_url = reverse(
            "admin:budo_app_kinder_change",
            args=(self.child.pk,),
        )
        self.add_url = reverse("admin:budo_app_kinder_add")

    def _create_child(self, kid_index):
        return Kinder.objects.create(
            kid_index=kid_index,
            kid_vorname="Initial",
            kid_nachname="Child",
            kid_birthday=date(2012, 7, 2),
            turnus_dauer=2,
            geschwister="None recorded",
            zeltwunsch="None recorded",
            schimmkenntnisse="Recorded",
            haftpflichtversicherung="Recorded",
            turnus=self.turnus,
            anmelder_vorname="Synthetic",
            anmelder_nachname="Guardian",
            anmelde_organisation="Synthetic organisation",
            anmelder_email="guardian@example.test",
            anmelder_mobil="+43000000000",
            hauptversichert_bei="Synthetic insurer",
            rechnungsadresse="Synthetic street 1",
            rechnung_plz=1010,
            rechnung_ort="Vienna",
            rechnung_land="Austria",
        )

    def _change_payload(self, **overrides):
        self.child.refresh_from_db()
        payload = {
            "kid_index": self.child.kid_index,
            "kid_vorname": self.child.kid_vorname,
            "kid_nachname": self.child.kid_nachname,
            "kid_birthday": self.child.kid_birthday.isoformat(),
            "turnus_dauer": str(self.child.turnus_dauer),
            "geschwister": self.child.geschwister,
            "zeltwunsch": self.child.zeltwunsch,
            "schimmkenntnisse": self.child.schimmkenntnisse,
            "haftpflichtversicherung": self.child.haftpflichtversicherung,
            "turnus": str(self.turnus.pk),
            "anmelder_vorname": self.child.anmelder_vorname,
            "anmelder_nachname": self.child.anmelder_nachname,
            "anmelde_organisation": self.child.anmelde_organisation,
            "anmelder_email": self.child.anmelder_email,
            "anmelder_mobil": self.child.anmelder_mobil,
            "hauptversichert_bei": self.child.hauptversichert_bei,
            "rechnungsadresse": self.child.rechnungsadresse,
            "rechnung_plz": str(self.child.rechnung_plz),
            "rechnung_ort": self.child.rechnung_ort,
            "rechnung_land": self.child.rechnung_land,
            "pfand": str(self.child.pfand),
            "happy_cleaning_number_version": str(
                self.child.happy_cleaning_number_version
            ),
            # Accepted by the old form so mutation tests reach its writer.
            # The adopted form must ignore this untrusted, read-only value.
            "edit_version": str(self.child.edit_version),
            "schwerpunkt_w1": str(self.focus_w1.pk),
            "schwerpunkt_w2": str(self.focus_w2.pk),
            "_save": "Save",
        }
        payload.update(overrides)
        return payload

    def _assert_links(self, *expected):
        self.assertEqual(
            set(self.child.schwerpunkte.values_list("pk", flat=True)),
            {focus.pk for focus in expected},
        )

    def _through_ids(self):
        through = Kinder.schwerpunkte.through
        return set(
            through.objects.filter(kinder_id=self.child.pk).values_list(
                "pk",
                flat=True,
            )
        )

    def _save_kinder_inline(self, focus, *, child, delete=False):
        request = RequestFactory().post("/synthetic-admin-inline/")
        request.user = self.user
        model_admin = admin.site._registry[Schwerpunkte]
        inline = next(
            candidate
            for candidate in model_admin.get_inline_instances(request, focus)
            if candidate.model is Kinder.schwerpunkte.through
        )
        formset_class = inline.get_formset(request, focus)
        prefix = formset_class.get_default_prefix()
        through = Kinder.schwerpunkte.through
        existing = through.objects.filter(
            kinder_id=child.pk,
            schwerpunkte_id=focus.pk,
        ).first()
        data = {
            f"{prefix}-TOTAL_FORMS": "1",
            f"{prefix}-INITIAL_FORMS": "1" if existing else "0",
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
            f"{prefix}-0-kinder": str(child.pk),
        }
        if existing:
            data[f"{prefix}-0-id"] = str(existing.pk)
        if delete:
            data[f"{prefix}-0-DELETE"] = "on"

        formset = formset_class(data=data, instance=focus, prefix=prefix)
        self.assertTrue(formset.is_valid(), formset.errors)
        model_admin.save_formset(
            request,
            form=None,
            formset=formset,
            change=True,
        )

    def test_edit_version_is_not_an_editable_admin_field(self):
        response = self.client.get(self.change_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="edit_version"')

    def test_turnus_is_selectable_on_add_and_readonly_on_change(self):
        add_response = self.client.get(self.add_url)
        change_response = self.client.get(self.change_url)

        self.assertEqual(add_response.status_code, 200)
        self.assertContains(add_response, 'name="turnus"')
        self.assertEqual(change_response.status_code, 200)
        self.assertNotContains(change_response, 'name="turnus"')

    def test_existing_child_cannot_be_reassigned_to_another_turnus(self):
        response = self.client.post(
            self.change_url,
            self._change_payload(
                kid_vorname="Updated without transfer",
                turnus=str(self.foreign_turnus.pk),
            ),
        )

        self.assertEqual(response.status_code, 302)
        self.child.refresh_from_db()
        self.assertEqual(self.child.kid_vorname, "Updated without transfer")
        self.assertEqual(self.child.turnus_id, self.turnus.id)

    def test_fixed_week_fields_are_scoped_to_the_child_turnus(self):
        form = KinderAdminForm(instance=self.child)

        self.assertEqual(
            set(form.fields["schwerpunkt_w1"].queryset.values_list(
                "id",
                flat=True,
            )),
            {self.focus_w1.id, self.focus_w1_alternative.id},
        )
        self.assertEqual(
            set(form.fields["schwerpunkt_w2"].queryset.values_list(
                "id",
                flat=True,
            )),
            {self.focus_w2.id},
        )

        foreign_only_child = self._create_child(
            "SYNTHETIC-ADMIN-FOREIGN-INITIAL"
        )
        foreign_only_child.schwerpunkte.add(self.foreign_focus)
        foreign_only_form = KinderAdminForm(instance=foreign_only_child)
        self.assertIsNone(
            foreign_only_form.fields["schwerpunkt_w1"].initial
        )

    def test_add_rejects_foreign_focus_without_leaking_its_label(self):
        payload = self._change_payload(
            kid_index="SYNTHETIC-ADMIN-FOREIGN-ADD",
            schwerpunkt_w1=str(self.foreign_focus.id),
        )

        response = self.client.post(self.add_url, payload)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Kinder.objects.filter(
                kid_index="SYNTHETIC-ADMIN-FOREIGN-ADD",
            ).exists()
        )
        self.assertNotContains(response, self.foreign_focus.swp_name)

    def test_add_rejects_malformed_turnus_with_empty_scoped_choices(self):
        payload = self._change_payload(
            kid_index="SYNTHETIC-ADMIN-MALFORMED-TURNUS",
            turnus="not-a-turnus-id",
        )

        response = self.client.post(self.add_url, payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice")
        self.assertFalse(
            Kinder.objects.filter(
                kid_index="SYNTHETIC-ADMIN-MALFORMED-TURNUS",
            ).exists()
        )
        self.assertNotContains(response, self.focus_w1.swp_name)
        self.assertNotContains(response, self.focus_w2.swp_name)
        self.assertNotContains(response, self.foreign_focus.swp_name)

    def test_add_accepts_selected_turnus_and_its_scoped_focuses(self):
        payload = self._change_payload(
            kid_index="SYNTHETIC-ADMIN-SCOPED-ADD",
        )

        response = self.client.post(self.add_url, payload)

        self.assertEqual(response.status_code, 302)
        added_child = Kinder.objects.get(
            kid_index="SYNTHETIC-ADMIN-SCOPED-ADD",
        )
        self.assertEqual(added_child.turnus_id, self.turnus.id)
        self.assertEqual(added_child.edit_version, 1)
        self.assertEqual(
            set(added_child.schwerpunkte.values_list("id", flat=True)),
            {self.focus_w1.id, self.focus_w2.id},
        )

    def test_scalar_edit_bumps_version_once_and_preserves_every_link(self):
        response = self.client.post(
            self.change_url,
            self._change_payload(kid_vorname="Updated"),
        )

        self.assertEqual(response.status_code, 302)
        self.child.refresh_from_db()
        self.assertEqual(self.child.kid_vorname, "Updated")
        self.assertEqual(self.child.edit_version, 2)
        self._assert_links(
            self.focus_w1,
            self.focus_w2,
            self.focus_u,
            self.foreign_focus,
        )

    def test_swp_edit_bumps_once_and_preserves_u_and_foreign_links(self):
        response = self.client.post(
            self.change_url,
            self._change_payload(
                schwerpunkt_w1=str(self.focus_w1_alternative.pk),
            ),
        )

        self.assertEqual(response.status_code, 302)
        self.child.refresh_from_db()
        self.assertEqual(self.child.edit_version, 2)
        self._assert_links(
            self.focus_w1_alternative,
            self.focus_w2,
            self.focus_u,
            self.foreign_focus,
        )

    def test_combined_scalar_and_swp_edit_bumps_exactly_once(self):
        response = self.client.post(
            self.change_url,
            self._change_payload(
                kid_vorname="Combined update",
                schwerpunkt_w1=str(self.focus_w1_alternative.pk),
            ),
        )

        self.assertEqual(response.status_code, 302)
        self.child.refresh_from_db()
        self.assertEqual(self.child.kid_vorname, "Combined update")
        self.assertEqual(self.child.edit_version, 2)
        self._assert_links(
            self.focus_w1_alternative,
            self.focus_w2,
            self.focus_u,
            self.foreign_focus,
        )

    def test_unchanged_submission_does_not_bump_or_rewrite_links(self):
        original_through_ids = self._through_ids()

        response = self.client.post(
            self.change_url,
            self._change_payload(),
        )

        self.assertEqual(response.status_code, 302)
        self.child.refresh_from_db()
        self.assertEqual(self.child.edit_version, 1)
        self.assertEqual(self._through_ids(), original_through_ids)
        self._assert_links(
            self.focus_w1,
            self.focus_w2,
            self.focus_u,
            self.foreign_focus,
        )

    def test_unchanged_submission_preserves_multiple_same_period_links(self):
        self.child.schwerpunkte.add(self.focus_w1_alternative)
        original_through_ids = self._through_ids()

        response = self.client.post(
            self.change_url,
            self._change_payload(),
        )

        self.assertEqual(response.status_code, 302)
        self.child.refresh_from_db()
        self.assertEqual(self.child.edit_version, 1)
        self.assertEqual(self._through_ids(), original_through_ids)
        self._assert_links(
            self.focus_w1,
            self.focus_w1_alternative,
            self.focus_w2,
            self.focus_u,
            self.foreign_focus,
        )

    def test_scalar_edit_preserves_multiple_same_period_links(self):
        self.child.schwerpunkte.add(self.focus_w1_alternative)

        response = self.client.post(
            self.change_url,
            self._change_payload(kid_vorname="Scalar only"),
        )

        self.assertEqual(response.status_code, 302)
        self.child.refresh_from_db()
        self.assertEqual(self.child.kid_vorname, "Scalar only")
        self.assertEqual(self.child.edit_version, 2)
        self._assert_links(
            self.focus_w1,
            self.focus_w1_alternative,
            self.focus_w2,
            self.focus_u,
            self.foreign_focus,
        )

    def test_intentional_week_change_replaces_multiple_same_period_links(self):
        replacement = Schwerpunkte.objects.create(
            swp_name="Synthetic intentional replacement",
            schwerpunktzeit=self.period_w1,
        )
        self.child.schwerpunkte.add(self.focus_w1_alternative)

        response = self.client.post(
            self.change_url,
            self._change_payload(schwerpunkt_w1=str(replacement.id)),
        )

        self.assertEqual(response.status_code, 302)
        self.child.refresh_from_db()
        self.assertEqual(self.child.edit_version, 2)
        self._assert_links(
            replacement,
            self.focus_w2,
            self.focus_u,
            self.foreign_focus,
        )

    def test_uncovered_admin_edit_persists_without_bumping(self):
        response = self.client.post(
            self.change_url,
            self._change_payload(anwesend="true"),
        )

        self.assertEqual(response.status_code, 302)
        self.child.refresh_from_db()
        self.assertIs(self.child.anwesend, True)
        self.assertEqual(self.child.edit_version, 1)
        self._assert_links(
            self.focus_w1,
            self.focus_w2,
            self.focus_u,
            self.foreign_focus,
        )

    def test_schwerpunkte_inline_add_bumps_and_preserves_other_links(self):
        self._save_kinder_inline(
            self.focus_w1_alternative,
            child=self.child,
        )

        self.child.refresh_from_db()
        self.assertEqual(self.child.edit_version, 2)
        self._assert_links(
            self.focus_w1,
            self.focus_w1_alternative,
            self.focus_w2,
            self.focus_u,
            self.foreign_focus,
        )

    def test_schwerpunkte_inline_delete_bumps_and_preserves_other_links(self):
        self._save_kinder_inline(
            self.focus_w1,
            child=self.child,
            delete=True,
        )

        self.child.refresh_from_db()
        self.assertEqual(self.child.edit_version, 2)
        self._assert_links(
            self.focus_w2,
            self.focus_u,
            self.foreign_focus,
        )

    def test_inline_deletes_uncovered_nullable_and_foreign_legacy_links(self):
        self.child.schwerpunkte.add(self.nullable_period_focus)

        self._save_kinder_inline(
            self.nullable_period_focus,
            child=self.child,
            delete=True,
        )
        self._save_kinder_inline(
            self.foreign_focus,
            child=self.child,
            delete=True,
        )

        self.child.refresh_from_db()
        self.assertEqual(self.child.edit_version, 1)
        self._assert_links(
            self.focus_w1,
            self.focus_w2,
            self.focus_u,
        )

    def test_inline_rejects_new_cross_turnus_link_without_mutation(self):
        foreign_child = self._create_child(
            "SYNTHETIC-ADMIN-FOREIGN-INLINE"
        )
        Kinder.objects.filter(pk=foreign_child.pk).update(
            turnus=self.foreign_turnus,
        )
        foreign_child.refresh_from_db()

        with self.assertRaisesRegex(
            ChildWriteScopeError,
            "unavailable in the active Turnus",
        ):
            self._save_kinder_inline(
                self.focus_w1,
                child=foreign_child,
            )

        self.assertFalse(
            foreign_child.schwerpunkte.filter(pk=self.focus_w1.pk).exists()
        )
