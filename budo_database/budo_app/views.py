from .models import Meal, Schwerpunkte
from django.shortcuts import redirect
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.template import loader
from django.urls import reverse_lazy
from django.forms import modelformset_factory
from django import forms
from datetime import datetime
from django.conf import settings
from django.contrib import messages
from . import models
from .models import Kinder, Notizen, Schwerpunkte, Meal, Profil, Auslagerorte
from django.views.generic import DetailView
from django.views.generic.edit import CreateView, UpdateView
from .forms import NotizForm, CheckInForm, UploadForm, CheckOutForm, MealChoiceForm, SchwerpunktForm, AuslagerForm
from copy import deepcopy
from django.contrib.auth.mixins import LoginRequiredMixin
from itertools import groupby
from django.views.decorators.http import require_POST
import json


from .excelProcessor import process_excel, postprocessing


def budo_app(request):
    template = loader.get_template('main.html')
    checked_in_kids = len(models.Kinder.objects.all())
    kids = models.Kinder.objects.all()
    context = {
        "kids": kids,
        "checked_in_kids": checked_in_kids
    }
    return HttpResponse(template.render(context, request))


@login_required
def uploadFile(request):
    template = loader.get_template('upload-file.html')
    documents = models.Turnus.objects.all()
    context = {
        "documents": documents,
    }
    if request.method == "POST":
        upload_form = UploadForm(request.POST)
        context["upload_form"] = upload_form
        if upload_form.is_valid():
            process_excel()
    else:
        upload_form = UploadForm()
        context["upload_form"] = upload_form

    return HttpResponse(template.render(context, request))


@login_required
def kids_list(request):
    kids = models.Kinder.objects.all()
    template = loader.get_template('kids_list.html')
    context = {
        'kids': kids,
    }
    return HttpResponse(template.render(context, request))


@login_required
def zuganreise(request):
    kids = models.Kinder.objects.all()
    zugabreise_count = models.Kinder.get_zugabreise_count()
    template = loader.get_template('zuganreise.html')
    context = {
        'kids': kids,
        'zugabreise_count': zugabreise_count,
    }
    return HttpResponse(template.render(context, request))


@csrf_exempt
def toggle_zug_abreise(request):
    if request.method == 'POST':
        kid_id = request.POST.get('id')
        kid = Kinder.objects.get(id=kid_id)
        kid.zug_abreise = not kid.zug_abreise
        kid.save()

        # Get the updated count
        zugabreise_count = Kinder.objects.filter(zug_abreise=True).count()

        return JsonResponse({'status': 'success', 'new_count': zugabreise_count})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@csrf_exempt
@require_POST
def update_notiz_abreise(request):
    data = json.loads(request.body)
    kid_id = data.get('id')
    new_notiz_abreise = data.get('notiz_abreise')

    try:
        kid = Kinder.objects.get(id=kid_id)
        kid.notiz_abreise = new_notiz_abreise
        kid.save()
        return JsonResponse({'status': 'success'})
    except Kinder.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Kid not found'})


@login_required
def kid_details(request, id):
    this_kid = models.Kinder.objects.get(id=id)
    kids = models.Kinder.objects.all().values()
    template = loader.get_template('kids_data.html')
    today = datetime.today().strftime('%Y-%m-%d')
    notizen = this_kid.notizen.all()

    context = {
        "today_date": today,
        "Kinder": this_kid,
        "Notizen": notizen,
        "kids": kids,
    }

    if request.method == 'POST':
        form = NotizForm(request.POST)
        context["form"] = form
        if form.is_valid():
            notiz = form.save(commit=False)
            notiz.kinder = this_kid
            notiz.added_by = request.user
            notiz.save()
            return redirect('kid_details', id=id)
    else:
        form = NotizForm()

    context["form"] = form

    return HttpResponse(template.render(context, request))


@login_required
def check_in(request, id):
    this_kid = models.Kinder.objects.get(id=id)
    original_kid = deepcopy(this_kid)
    kids = models.Kinder.objects.all().values()
    template = loader.get_template('check_in.html')
    today = datetime.today().strftime('%Y-%m-%d')
    today_time = datetime.today().strftime('%d.%m.@%H:%M')
    context = {
        "today_date": today,
        'Kinder': this_kid,
        "kids": kids,
    }

    if request.method == 'POST':
        check_in_form = CheckInForm(request.POST, instance=this_kid)
        notiz_form = NotizForm(request.POST)
        context["check_in_form"] = check_in_form
        context["notiz_form"] = notiz_form
        if notiz_form.is_valid():
            notiz = notiz_form.cleaned_data.get('notiz')
            if notiz:
                notiz = notiz_form.save(commit=False)
                notiz.kinder = this_kid
                notiz.added_by = request.user
                notiz.save()
        if check_in_form.is_valid():
            this_kid = check_in_form.save(commit=False)
            this_kid.anwesend = True
            # print(this_kid.check_in_date)
            # print(
            #     f'Turnusbeginn: {this_kid.turnus.turnus_beginn.strftime("%Y-%m-%d")}')
            # print(datetime.today().strftime("%Y-%m-%d"))
            if this_kid.check_in_date.strftime("%Y-%m-%d") != this_kid.turnus.turnus_beginn.strftime("%Y-%m-%d"):
                this_kid.late_anreise = this_kid.check_in_date
                if original_kid.check_in_date != None:
                    this_kid.check_in_date = original_kid.check_in_date

            this_kid.save()
            return redirect('kid_details', id=id)
    else:
        check_in_form = CheckInForm()
        notiz_form = NotizForm()
        context["check_in_form"] = check_in_form
        context["notiz_form"] = notiz_form

    return HttpResponse(template.render(context, request))


@login_required
def check_out(request, id):
    this_kid = models.Kinder.objects.get(id=id)
    original_kid = deepcopy(this_kid)
    kids = models.Kinder.objects.all().values()
    template = loader.get_template('check_out.html')
    today = datetime.today().strftime('%Y-%m-%d')
    context = {
        "today_date": today,
        'Kinder': this_kid,
        "kids": kids,
    }

    if request.method == 'POST':
        check_out_form = CheckOutForm(request.POST, instance=this_kid)
        notiz_form = NotizForm(request.POST)
        context["check_out_form"] = check_out_form
        context["notiz_form"] = notiz_form
        if notiz_form.is_valid():
            notiz = notiz_form.cleaned_data.get('notiz')
            if notiz:
                notiz = notiz_form.save(commit=False)
                notiz.kinder = this_kid
                notiz.added_by = request.user
                notiz.save()
        if check_out_form.is_valid():
            this_kid = check_out_form.save(commit=False)
            this_kid.anwesend = False
            this_kid.e_card = False
            this_kid.ausweis = False
            if this_kid.early_abreise_date.strftime("%Y-%m-%d") == this_kid.turnus.get_turnus_ende().strftime("%Y-%m-%d"):

                this_kid.early_abreise_date = None

            this_kid.save()
            return redirect('kid_details', id=id)
    else:
        check_out_form = CheckOutForm()
        notiz_form = NotizForm()
        context["check_out_form"] = check_out_form
        context["notiz_form"] = notiz_form

    return HttpResponse(template.render(context, request))


def postprocess(request):
    postprocessing()


@login_required
def serienbrief(request):
    kids = models.Kinder.objects.all()
    template = loader.get_template('serienbrief.html')
    context = {
        "kids": kids,
    }

    return HttpResponse(template.render(context, request))


@login_required
def murdergame(request):
    kids = models.Kinder.objects.filter(anwesend=True)
    team = models.Profil.objects.all()
    template = loader.get_template('murdergame.html')
    context = {
        "kids": kids,
        "team": team,
    }

    return HttpResponse(template.render(context, request))


class SchwerpunkteUpdate(LoginRequiredMixin, UpdateView):
    model = Schwerpunkte
    form_class = SchwerpunktForm
    template_name = "schwerpunkt-form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'updaten'
        return context

    def form_valid(self, form):
        messages.success(self.request, "Schwerpunkt upgedatet!")
        return super(SchwerpunkteUpdate, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy('schwerpunkt-detail', kwargs={'pk': self.object.pk})


class SchwerpunkteDetail(LoginRequiredMixin, DetailView):
    model = Schwerpunkte
    template_name = 'schwerpunkt-detail.html'
    context_object_name = 'schwerpunkt'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        meals_by_day = {}
        for meal in self.object.meals.all():
            if meal.day not in meals_by_day:
                meals_by_day[meal.day] = []
            meals_by_day[meal.day].append(meal)
        context['meals_by_day'] = meals_by_day
        context["google_maps_api_key"] = settings.GOOGLE_MAPS_API_KEY
        return context


class SchwerpunkteCreate(LoginRequiredMixin, CreateView):
    model = Schwerpunkte
    form_class = SchwerpunktForm
    template_name = 'schwerpunkt-form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'erstellen'
        return context

    def form_valid(self, form):
        messages.success(self.request, "Schwerpunkt hinzugefügt!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('schwerpunkt-detail', kwargs={'pk': self.object.pk})


# Auslagerorte
class AuslagerorteUpdate(LoginRequiredMixin, UpdateView):
    model = Auslagerorte
    form_class = AuslagerForm
    template_name = "auslagerorte-form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'updaten'
        return context

    def form_valid(self, form):
        messages.success(self.request, "Auslagerort upgedatet!")
        return super(AuslagerorteUpdate, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy('auslagerorte-detail', kwargs={'pk': self.object.pk})


class AuslagerorteDetail(LoginRequiredMixin, DetailView):
    model = Auslagerorte
    template_name = 'auslagerorte-detail.html'
    context_object_name = 'ort'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["google_maps_api_key"] = settings.GOOGLE_MAPS_API_KEY
        return context


class AuslagerorteCreate(LoginRequiredMixin, CreateView):
    model = Auslagerorte
    form_class = AuslagerForm
    template_name = 'auslagerorte-form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'erstellen'
        return context

    def form_valid(self, form):
        messages.success(self.request, "Auslagerort hinzugefügt!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('auslagerorte-detail', kwargs={'pk': self.object.pk})


@login_required
def auslagerorte_list(request):
    template = loader.get_template('auslagerorte-list.html')

    current_user = request.user

    kids = Kinder.objects.all()
    auslagerorte = Auslagerorte.objects.all()
    context = {
        "kids": kids,
        "auslagerorte": auslagerorte,
    }

    return HttpResponse(template.render(context, request))


class MealUpdate(LoginRequiredMixin, UpdateView):
    model = Schwerpunkte
    form_class = MealChoiceForm
    template_name = "swpmeals.html"
    success_url = reverse_lazy('swp-dashboard')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        MealFormSet = modelformset_factory(Meal, form=MealChoiceForm, extra=0)
        if self.request.POST:
            data['meal_formset'] = MealFormSet(
                self.request.POST, queryset=Meal.objects.filter(schwerpunkt=self.object))
        else:
            data['meal_formset'] = MealFormSet(
                queryset=Meal.objects.filter(schwerpunkt=self.object))
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        meal_formset = context['meal_formset']
        if meal_formset.is_valid():
            meal_formset.save()
            return redirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))


@login_required
def swp_dashboard(request):
    template = loader.get_template('swp-dashboard.html')

    current_user = request.user
    profil = Profil.objects.get(user=current_user)
    kids = Kinder.objects.all()
    anzahl_kids = Kinder.objects.all().count()
    kids_zug_anreise_count = Kinder.objects.filter(zug_anreise=True).count()
    kids_zug_abreise_count = Kinder.objects.filter(zug_abreise=True).count()
    male_kids_count = Kinder.objects.filter(sex="männlich").count()
    female_kids_count = Kinder.objects.filter(sex="weiblich").count()
    diverse_kids_count = Kinder.objects.exclude(
        sex__in=["männlich", "weiblich"]).count()
    kids_mit_budo_erfahrung = Kinder.objects.filter(
        budo_erfahrung=True).count()
    # geburtstagskinder = [
    #     kid for kid in kids if kid.is_birthday_during_turnus()]
    geburtstagskinder = sorted(
        [kid for kid in kids if kid.is_birthday_during_turnus()],
        key=lambda kid: (kid.kid_birthday.month, kid.kid_birthday.day)
    )
    geburtstage = len(geburtstagskinder)
    eingecheckte_kids = Kinder.objects.filter(anwesend=True).count()
    team = Profil.objects.all()

    medikamente = [kid for kid in kids if kid.get_clean_drugs()]
    gesundheit = [kid for kid in kids if kid.get_clean_illness()]
    kids_attention = [kid for kid in kids if (
        kid.get_clean_drugs() or kid.get_clean_illness())]
    ersties = Kinder.objects.filter(budo_erfahrung=False)
    ersties_count = ersties.count()
    swps = Schwerpunkte.objects.all()
    context = {
        "profil": profil,
        "kids": kids,
        "kids_zug_anreise_count": kids_zug_anreise_count,
        "kids_zug_abreise_count": kids_zug_abreise_count,
        "male_kids_count": male_kids_count,
        "female_kids_count": female_kids_count,
        "diverse_kids_count": diverse_kids_count,
        "kids_mit_budo_erfahrung": kids_mit_budo_erfahrung,
        "geburtstagskinder": geburtstagskinder,
        "geburtstage": geburtstage,
        "eingecheckte_kids": eingecheckte_kids,
        "anzahl_kids": anzahl_kids,
        "team": team,
        "medikamente": medikamente,
        "gesundheit": gesundheit,
        "kids_attention": kids_attention,
        "ersties": ersties,
        "ersties_count": ersties_count,
        "swps": swps,
    }

    return HttpResponse(template.render(context, request))
