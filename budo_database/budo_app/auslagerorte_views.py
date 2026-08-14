import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import DetailView
from django.views.generic.edit import CreateView, FormView, UpdateView

from . import models
from .forms import AuslagerForm, AuslagerNotizForm, AuslagerorteImageForm
from .location_services import BUDO_PLACE_NAME, update_auslagerorte_coordinates
from .memberships import membership_scoped_read
from .models import (
    Auslagerorte,
    AuslagerorteImage,
    Schwerpunkte,
)
from .react_views import ReactPageTemplateMixin, render_react_page

logger = logging.getLogger(__name__)

_ADDRESS_FIELDS = ("strasse", "ort", "bundesland", "postleitzahl", "land")


@method_decorator(membership_scoped_read, name="dispatch")
class AuslagerorteUpdate(
    ReactPageTemplateMixin,
    LoginRequiredMixin,
    UpdateView,
):
    model = Auslagerorte
    form_class = AuslagerForm

    def get_context_data(self, **kwargs):
        active_turnus = self.request.active_turnus
        schwerpunkte = Schwerpunkte.objects.filter(
            schwerpunktzeit__turnus=active_turnus)
        auslagerorte = Auslagerorte.objects.all()
        kids = models.Kinder.objects.filter(turnus=active_turnus)
        context = super().get_context_data(**kwargs)
        context['action'] = 'updaten'
        context['schwerpunkte'] = schwerpunkte
        context['auslagerorte'] = auslagerorte
        context['kids'] = kids
        return context

    def form_valid(self, form):
        form.instance._maps_link_changed = 'maps_link' in form.changed_data
        form.instance._maps_link_parkspot_changed = (
            'maps_link_parkspot' in form.changed_data
        )
        form.instance = update_auslagerorte_coordinates(form.instance)
        for warning in getattr(form.instance, '_location_warnings', []):
            messages.warning(self.request, warning)
        messages.success(self.request, "Auslagerort upgedatet!")
        return super(AuslagerorteUpdate, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy('auslagerorte-detail', kwargs={'pk': self.object.pk})


@method_decorator(membership_scoped_read, name="dispatch")
class AuslagerorteDetail(
    ReactPageTemplateMixin,
    LoginRequiredMixin,
    DetailView,
):
    model = Auslagerorte
    context_object_name = 'ort'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_turnus = self.request.active_turnus
        schwerpunkte = Schwerpunkte.objects.filter(
            schwerpunktzeit__turnus=active_turnus)
        auslagerorte = Auslagerorte.objects.all()
        kids = models.Kinder.objects.filter(turnus=active_turnus)

        context.update({
            'schwerpunkte': schwerpunkte,
            'auslagerorte': auslagerorte,
            'kids': kids,
            'form': AuslagerorteImageForm(),
            'auslagernotiz_form': AuslagerNotizForm(),
        })

        ort = self.get_object()
        auslagerorte_data = [{
            'id': ort.id,
            'name': ort.name,
            'koordinaten': ort.koordinaten,
            'kind': 'auslagerorte',
        }]

        try:
            budo_ort = Auslagerorte.objects.get(name=BUDO_PLACE_NAME)
            auslagerorte_data.append({
                'id': budo_ort.id,
                'name': budo_ort.name,
                'koordinaten': budo_ort.koordinaten,
                'kind': 'auslagerorte',
            })
        except Auslagerorte.DoesNotExist:
            pass

        context['orte_json'] = json.dumps({
            'orte': auslagerorte_data,
        })

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        auslagernotiz_form = AuslagerNotizForm(request.POST)
        uploaded_images = request.FILES.getlist('images')
        image_form = AuslagerorteImageForm(
            request.POST,
            request.FILES,
        ) if uploaded_images else None

        if auslagernotiz_form.is_valid() and (image_form is None or image_form.is_valid()):
            attempted_images = []
            try:
                with transaction.atomic():
                    notiz = auslagernotiz_form.save(commit=False)
                    notiz.auslagerort = self.object
                    notiz.added_by = request.user
                    notiz.save()
                    for uploaded_image in uploaded_images:
                        stored_image = AuslagerorteImage(
                            auslagerort=self.object,
                            notiz=notiz,
                            image=uploaded_image,
                        )
                        attempted_images.append(stored_image)
                        stored_image.save()
            except Exception:
                for stored_image in attempted_images:
                    name = stored_image.image.name
                    if not name or not stored_image.image._committed:
                        continue
                    try:
                        stored_image.image.storage.delete(name)
                    except Exception:
                        logger.exception(
                            "Failed to clean up comment image after upload failure"
                        )
                logger.exception("Location comment image upload failed")
                auslagernotiz_form.add_error(
                    None,
                    "Der Kommentar konnte nicht gespeichert werden. Bitte erneut versuchen.",
                )
            else:
                return redirect('auslagerorte-detail', pk=self.object.pk)

        context = self.get_context_data(object=self.object)
        context['auslagernotiz_form'] = auslagernotiz_form
        context['form'] = image_form or AuslagerorteImageForm()
        return self.render_to_response(context)


class AuslagerorteCreate(
    ReactPageTemplateMixin,
    LoginRequiredMixin,
    CreateView,
):
    model = Auslagerorte
    form_class = AuslagerForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'erstellen'
        return context

    def form_valid(self, form):
        # The reduced create form intentionally omits address controls. Apply
        # their cleaned empty values so the model's country default cannot
        # prevent reverse geocoding from filling the complete address.
        for field_name in _ADDRESS_FIELDS:
            if field_name not in form.data:
                setattr(form.instance, field_name, form.cleaned_data[field_name])
        form.instance = update_auslagerorte_coordinates(form.instance)
        for warning in getattr(form.instance, '_location_warnings', []):
            messages.warning(self.request, warning)
        messages.success(self.request, "Auslagerort hinzugefügt!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('auslagerorte-detail', kwargs={'pk': self.object.pk})


class AuslagerorteImageUpload(
    ReactPageTemplateMixin,
    LoginRequiredMixin,
    FormView,
):
    form_class = AuslagerorteImageForm

    def form_valid(self, form):
        auslagerort = get_object_or_404(Auslagerorte, pk=self.kwargs['pk'])
        attempted_images = []

        try:
            with transaction.atomic():
                for uploaded_image in form.cleaned_data['images']:
                    stored_image = AuslagerorteImage(
                        auslagerort=auslagerort,
                        image=uploaded_image,
                    )
                    attempted_images.append(stored_image)
                    stored_image.save()
        except Exception:
            for stored_image in attempted_images:
                name = stored_image.image.name
                if not name or not stored_image.image._committed:
                    continue
                try:
                    stored_image.image.storage.delete(name)
                except Exception:
                    logger.exception(
                        "Failed to clean up image object after batch upload failure"
                    )
            logger.exception("Location image batch upload failed")
            form.add_error(
                None,
                "Die Bilder konnten nicht gespeichert werden. Bitte erneut versuchen.",
            )
            return self.form_invalid(form)

        messages.success(self.request, "Bilder hochgeladen!")
        return redirect('auslagerorte-detail', pk=auslagerort.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['auslagerort'] = get_object_or_404(
            Auslagerorte, pk=self.kwargs['pk'])
        return context


@login_required
@membership_scoped_read
def auslagerorte_list(request):
    active_turnus = request.active_turnus
    kids = models.Kinder.objects.all().values()
    schwerpunkte = Schwerpunkte.objects.filter(
        schwerpunktzeit__turnus=active_turnus)
    auslagerorte = Auslagerorte.objects.all()
    auslagerorte_data = []
    for ort in auslagerorte:
        if ort:
            auslagerorte_data.append({
                'id': ort.id,
                'name': ort.name,
                'koordinaten': ort.koordinaten,
                'kind': 'auslagerorte',
            })
    context = {
        "kids": kids,
        "auslagerorte": auslagerorte,
        "schwerpunkte": schwerpunkte,
        "orte_json": json.dumps({
            'orte': auslagerorte_data,
        }),
    }

    return render_react_page(request, context)
