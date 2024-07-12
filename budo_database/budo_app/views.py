from .models import Profil
from django.http import FileResponse, HttpResponse
from .models import Meal, Schwerpunkte
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.template import loader
from django.urls import reverse_lazy
from django.db.models import Prefetch
from django.forms import modelformset_factory
from datetime import datetime
from django.conf import settings
from django.contrib import messages
from . import models
from .models import Kinder, Notizen, Schwerpunkte, Meal, Profil, Auslagerorte, AuslagerorteImage, SchwerpunktWahl, Schwerpunktzeit
from django.views.generic import DetailView
from django.views.generic.edit import CreateView, UpdateView, FormView
from .forms import NotizForm, CheckInForm, UploadForm, CheckOutForm, MealChoiceForm, SchwerpunktForm, AuslagerForm, AuslagerNotizForm, AuslagerorteImageForm, GeldForm
from copy import deepcopy
from django.contrib.auth.mixins import LoginRequiredMixin
from itertools import groupby
from django.views.decorators.http import require_POST
import os
import json
import toml
import csv


from .excelProcessor import process_excel, postprocessing
from .updateExcel import update_excel_file

info_file_path = os.path.join(settings.BASE_DIR, "info.toml")
info = toml.load(info_file_path)

# def get_related_data_for_user(user):
#     profil = Profil.objects.get(user=user)
#     active_turnus = profil.turnus
#     kids = Kinder.objects.filter(turnus=active_turnus)
#     schwerpunkte = Schwerpunkte.objects.filter(schwerpunktzeit__turnus=active_turnus)
#     auslagerorte = Auslagerorte.objects.filter(schwerpunkte__schwerpunktzeit__turnus=active_turnus).distinct()
#     return {
#         'kids': kids,
#         'schwerpunkte': schwerpunkte,
#         'auslagerorte': auslagerorte,
#     }


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
        upload_form = UploadForm(request.POST, request.FILES)
        context["upload_form"] = upload_form
        if upload_form.is_valid():
            turnus = upload_form.save()
            if 'uploadedFile' in request.FILES:
                process_excel()
    else:
        upload_form = UploadForm()
        context["upload_form"] = upload_form

    return HttpResponse(template.render(context, request))


def upload_excel(request, turnus_id):
    turnus = get_object_or_404(models.Turnus, id=turnus_id)
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES, instance=turnus)
        if form.is_valid():
            form.save()
            process_excel()
            return redirect('uploadFile')
    else:
        form = UploadForm(instance=turnus)
    return render(request, 'upload_excel.html', {'form': form, 'turnus': turnus})


@login_required
def kids_list(request):
    current_user = request.user
    if not current_user.is_authenticated:
        # Redirect to the login page if not authenticated
        return redirect('login')
    profil = Profil.objects.get(user=current_user)
    active_turnus = profil.turnus
    kids = models.Kinder.objects.filter(turnus=active_turnus)
    schwerpunkte = Schwerpunkte.objects.filter(
        schwerpunktzeit__turnus=active_turnus)
    auslagerorte = Auslagerorte.objects.all()
    template = loader.get_template('kids_list.html')
    context = {
        'kids': kids,
        'schwerpunkte': schwerpunkte,
        'auslagerorte': auslagerorte,
    }
    return HttpResponse(template.render(context, request))


@login_required
def zugabreise(request):
    current_user = request.user
    if not current_user.is_authenticated:
        # Redirect to the login page if not authenticated
        return redirect('login')
    profil = Profil.objects.get(user=current_user)
    active_turnus = profil.turnus
    kids = models.Kinder.objects.filter(
        turnus=active_turnus).order_by('-zug_abreise', 'kid_vorname')
    schwerpunkte = Schwerpunkte.objects.filter(
        schwerpunktzeit__turnus=active_turnus)
    auslagerorte = Auslagerorte.objects.all()
    zugabreise_count = models.Kinder.get_zugabreise_count(
        turnus=active_turnus)  # Pass the active turnus
    template = loader.get_template('zugabreise.html')
    context = {
        'kids': kids,
        'zugabreise_count': zugabreise_count,
        'schwerpunkte': schwerpunkte,
        'auslagerorte': auslagerorte,
    }
    return HttpResponse(template.render(context, request))


@login_required
def zuganreise(request):
    current_user = request.user
    profil = Profil.objects.get(user=current_user)
    active_turnus = profil.turnus
    kids = models.Kinder.objects.filter(
        turnus=active_turnus, zug_anreise=True).order_by('kid_vorname')
    kids_with_top_jugendticket_count = kids.filter(
        top_jugendticket=True).count()
    kids_without_top_jugendticket_count = kids.exclude(
        top_jugendticket=True).count()
    schwerpunkte = Schwerpunkte.objects.filter(
        schwerpunktzeit__turnus=active_turnus)
    auslagerorte = Auslagerorte.objects.all()
    zuganreise_count = models.Kinder.get_zuganreise_count(
        turnus=active_turnus)
    busunternehmen = info['busunternehmen']
    template = loader.get_template('zuganreise.html')
    context = {
        'kids': kids,
        'zuganreise_count': zuganreise_count,
        'schwerpunkte': schwerpunkte,
        'auslagerorte': auslagerorte,
        'kids_with_top_jugendticket_count': kids_with_top_jugendticket_count,
        'kids_without_top_jugendticket_count': kids_without_top_jugendticket_count,
        'busunternehmen': busunternehmen,
    }
    return HttpResponse(template.render(context, request))


@csrf_exempt
def toggle_zug_abreise(request):
    if request.method == 'POST':
        current_user = request.user
        profil = Profil.objects.get(user=current_user)
        active_turnus = profil.turnus
        kid_id = request.POST.get('id')
        kid = Kinder.objects.get(id=kid_id)
        kid.zug_abreise = not kid.zug_abreise
        kid.save()

        # Get the updated count
        zugabreise_count = Kinder.objects.filter(
            zug_abreise=True, turnus=active_turnus).count()

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
    current_user = request.user
    profil = Profil.objects.get(user=current_user)
    active_turnus = profil.turnus
    this_kid = models.Kinder.objects.get(id=id)
    kids = models.Kinder.objects.all().values()
    schwerpunkte = Schwerpunkte.objects.filter(
        schwerpunktzeit__turnus=active_turnus)
    auslagerorte = Auslagerorte.objects.all()
    template = loader.get_template('kids_data.html')
    today = datetime.today().strftime('%Y-%m-%d')
    notizen = this_kid.notizen.all()

    context = {
        "today_date": today,
        "Kinder": this_kid,
        "Notizen": notizen,
        "kids": kids,
        'schwerpunkte': schwerpunkte,
        'auslagerorte': auslagerorte,
    }

    if request.method == 'POST':
        notiz_form = NotizForm(request.POST)
        geld_form = GeldForm(request.POST)
        context["notiz_form"] = notiz_form
        context["geld_form"] = geld_form

        if notiz_form.is_valid():
            print("Notiz form is valid")
            notiz = notiz_form.cleaned_data.get('notiz')
            if notiz:
                print(notiz)
                notiz = notiz_form.save(commit=False)
                notiz.kinder = this_kid
                notiz.added_by = request.user
                notiz.save()

        if geld_form.is_valid():
            print("Geld form is valid")
            geld = geld_form.cleaned_data.get("amount")
            if geld:
                print(geld)
                geld = geld_form.save(commit=False)
                geld.kinder = this_kid
                geld.added_by = request.user
                geld.save()
            return redirect('kid_details', id=id)
        else:
            # Debugging statement
            print("Geld form is not valid:", geld_form.errors)
    else:
        notiz_form = NotizForm()
        geld_form = GeldForm()
        context["notiz_form"] = notiz_form
        context["geld_form"] = geld_form

    return HttpResponse(template.render(context, request))


@login_required
def check_in(request, id):
    current_user = request.user
    if not current_user.is_authenticated:
        # Redirect to the login page if not authenticated
        return redirect('login')
    profil = Profil.objects.get(user=current_user)
    active_turnus = profil.turnus
    this_kid = models.Kinder.objects.get(id=id)
    original_kid = deepcopy(this_kid)
    kids = models.Kinder.objects.all().values()
    schwerpunkte = Schwerpunkte.objects.filter(
        schwerpunktzeit__turnus=active_turnus)
    auslagerorte = Auslagerorte.objects.all()
    template = loader.get_template('check_in.html')
    today = datetime.today().strftime('%Y-%m-%d')
    today_time = datetime.today().strftime('%d.%m.@%H:%M')
    context = {
        "today_date": today,
        'Kinder': this_kid,
        "kids": kids,
        'schwerpunkte': schwerpunkte,
        'auslagerorte': auslagerorte,
    }

    if request.method == 'POST':
        check_in_form = CheckInForm(request.POST, instance=this_kid)
        notiz_form = NotizForm(request.POST)
        geld_form = GeldForm(request.POST)
        context["check_in_form"] = check_in_form
        context["notiz_form"] = notiz_form
        context["geld_form"] = geld_form
        if notiz_form.is_valid():
            notiz = notiz_form.cleaned_data.get('notiz')
            if notiz:
                notiz = notiz_form.save(commit=False)
                notiz.kinder = this_kid
                notiz.added_by = request.user
                notiz.save()
        if geld_form.is_valid():
            geld = geld_form.cleaned_data.get("amount")
            if geld:
                geld = geld_form.save(commit=False)
                geld.kinder = this_kid
                geld.added_by = request.user
                geld.save()
        if check_in_form.is_valid():
            this_kid = check_in_form.save(commit=False)
            this_kid.anwesend = True
            if this_kid.check_in_date.strftime("%Y-%m-%d") != this_kid.turnus.turnus_beginn.strftime("%Y-%m-%d"):
                this_kid.late_anreise = this_kid.check_in_date
                if original_kid.check_in_date != None:
                    this_kid.check_in_date = original_kid.check_in_date

            this_kid.save()
            return redirect('kid_details', id=id)
    else:
        check_in_form = CheckInForm()
        notiz_form = NotizForm()
        geld_form = GeldForm()
        context["check_in_form"] = check_in_form
        context["notiz_form"] = notiz_form
        context["geld_form"] = geld_form

    return HttpResponse(template.render(context, request))


@login_required
def check_out(request, id):
    current_user = request.user
    if not current_user.is_authenticated:
        # Redirect to the login page if not authenticated
        return redirect('login')
    profil = Profil.objects.get(user=current_user)
    active_turnus = profil.turnus
    this_kid = models.Kinder.objects.get(id=id)
    original_kid = deepcopy(this_kid)
    kids = models.Kinder.objects.all().values()
    schwerpunkte = Schwerpunkte.objects.filter(
        schwerpunktzeit__turnus=active_turnus)
    auslagerorte = Auslagerorte.objects.all()
    template = loader.get_template('check_out.html')
    today = datetime.today().strftime('%Y-%m-%d')
    context = {
        "today_date": today,
        'Kinder': this_kid,
        "kids": kids,
        'schwerpunkte': schwerpunkte,
        'auslagerorte': auslagerorte,
    }

    if request.method == 'POST':
        check_out_form = CheckOutForm(request.POST, instance=this_kid)
        notiz_form = NotizForm(request.POST)
        geld_form = GeldForm(request.POST)
        context["check_out_form"] = check_out_form
        context["notiz_form"] = notiz_form
        context["geld_form"] = geld_form
        if notiz_form.is_valid():
            notiz = notiz_form.cleaned_data.get('notiz')
            if notiz:
                notiz = notiz_form.save(commit=False)
                notiz.kinder = this_kid
                notiz.added_by = request.user
                notiz.save()
        if geld_form.is_valid():
            geld = geld_form.cleaned_data.get("amount")
            if geld:
                geld = geld_form.save(commit=False)
                geld.kinder = this_kid
                geld.added_by = request.user
                geld.save()
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
        geld_form = GeldForm(
            initial={'amount': -this_kid.get_taschengeld_sum()})
        context["check_out_form"] = check_out_form
        context["notiz_form"] = notiz_form
        context["geld_form"] = geld_form

    return HttpResponse(template.render(context, request))


def postprocess(request):
    postprocessing()


@login_required
def serienbrief(request):
    current_user = request.user
    if not current_user.is_authenticated:
        # Redirect to the login page if not authenticated
        return redirect('login')
    profil = Profil.objects.get(user=current_user)
    active_turnus = profil.turnus
    kids = models.Kinder.objects.filter(turnus=active_turnus)
    template = loader.get_template('serienbrief.html')
    context = {
        "kids": kids,
    }

    return HttpResponse(template.render(context, request))


@login_required
def murdergame(request):
    current_user = request.user
    if not current_user.is_authenticated:
        # Redirect to the login page if not authenticated
        return redirect('login')
    profil = Profil.objects.get(user=current_user)
    active_turnus = profil.turnus
    kids = models.Kinder.objects.filter(turnus=active_turnus, anwesend=True)
    team = models.Profil.objects.filter(turnus=active_turnus)
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
        current_user = self.request.user
        profil = Profil.objects.get(user=current_user)
        active_turnus = profil.turnus
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
        messages.success(self.request, "Schwerpunkt upgedatet!")
        return super(SchwerpunkteUpdate, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy('schwerpunkt-detail', kwargs={'pk': self.object.pk})


class SchwerpunkteDetail(LoginRequiredMixin, DetailView):
    model = Schwerpunkte
    template_name = 'schwerpunkt-detail.html'
    context_object_name = 'schwerpunkt'

    def get_context_data(self, **kwargs):
        current_user = self.request.user
        profil = Profil.objects.get(user=current_user)
        active_turnus = profil.turnus
        schwerpunkte = Schwerpunkte.objects.filter(
            schwerpunktzeit__turnus=active_turnus)
        auslagerorte = Auslagerorte.objects.all()
        kids = models.Kinder.objects.filter(turnus=active_turnus)
        context = super().get_context_data(**kwargs)
        meals_by_day = {}
        for meal in self.object.meals.all():
            if meal.day not in meals_by_day:
                meals_by_day[meal.day] = []
            meals_by_day[meal.day].append(meal)
        context['meals_by_day'] = meals_by_day
        context['schwerpunkte'] = schwerpunkte
        context['auslagerorte'] = auslagerorte
        context['kids'] = kids

        # Add the single schwerpunkt data in the same format as auslagerorte_list
        schwerpunkt = self.get_object()
        auslagerorte_data = [{
            'id': schwerpunkt.id,
            'name': schwerpunkt.swp_name,
            'koordinaten': schwerpunkt.ort.koordinaten if schwerpunkt.ort else '',
            'kind': 'schwerpunkt',
        }]

        try:
            if schwerpunkt.ort.name != "BuDo":
                budo_ort = Auslagerorte.objects.get(name="BuDo")
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
        current_user = self.request.user
        profil = Profil.objects.get(user=current_user)
        active_turnus = profil.turnus
        schwerpunkte = Schwerpunkte.objects.filter(
            schwerpunktzeit__turnus=active_turnus)
        auslagerorte = Auslagerorte.objects.all()
        kids = models.Kinder.objects.filter(turnus=active_turnus)
        context = super().get_context_data(**kwargs)
        context['action'] = 'updaten'
        context['schwerpunkte'] = schwerpunkte
        context['auslagerorte'] = auslagerorte
        context['kids'] = kids
        print(context)
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
        current_user = self.request.user
        profil = Profil.objects.get(user=current_user)
        active_turnus = profil.turnus
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
            budo_ort = Auslagerorte.objects.get(name="BuDo")
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

        if auslagernotiz_form.is_valid():
            notiz = auslagernotiz_form.save(commit=False)
            notiz.auslagerort = self.object
            notiz.added_by = request.user
            notiz.save()
            return redirect('auslagerorte-detail', pk=self.object.pk)

        context = self.get_context_data(object=self.object)
        context['auslagernotiz_form'] = auslagernotiz_form
        return self.render_to_response(context)


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


class AuslagerorteImageUpload(LoginRequiredMixin, FormView):
    form_class = AuslagerorteImageForm
    template_name = 'auslagerorte-image-upload.html'

    def form_valid(self, form):
        auslagerort = get_object_or_404(Auslagerorte, pk=self.kwargs['pk'])
        images = form.cleaned_data['images']
        for image in images:
            AuslagerorteImage.objects.create(
                auslagerort=auslagerort, image=image)
        messages.success(self.request, "Bilder hochgeladen!")
        return redirect('auslagerorte-detail', pk=auslagerort.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['auslagerort'] = get_object_or_404(
            Auslagerorte, pk=self.kwargs['pk'])
        return context


@login_required
def auslagerorte_list(request):
    template = loader.get_template('auslagerorte-list.html')

    current_user = request.user
    if not current_user.is_authenticated:
        # Redirect to the login page if not authenticated
        return redirect('login')
    profil = Profil.objects.get(user=current_user)
    active_turnus = profil.turnus
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

    return HttpResponse(template.render(context, request))


class MealUpdate(LoginRequiredMixin, UpdateView):
    model = Schwerpunkte
    form_class = MealChoiceForm
    template_name = "swpmeals.html"

    def get_success_url(self):
        return reverse_lazy('schwerpunkt-detail', kwargs={'pk': self.object.pk})

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
    if not current_user.is_authenticated:
        # Redirect to the login page if not authenticated
        return redirect('login')
    profil = Profil.objects.get(user=current_user)
    active_turnus = profil.turnus

    kids = Kinder.objects.filter(turnus=active_turnus)

    schwerpunkte = Schwerpunkte.objects.filter(
        schwerpunktzeit__turnus=active_turnus)

    schwerpunkte_u = Schwerpunkte.objects.filter(
        schwerpunktzeit__turnus=active_turnus, schwerpunktzeit__woche='u')

    schwerpunkte_data = []
    for swp in schwerpunkte:
        if swp.ort:
            schwerpunkte_data.append({
                'id': swp.id,
                'name': swp.swp_name,
                'koordinaten': swp.ort.koordinaten,
                'kind': 'schwerpunkt',
            })
    auslagerorte = Auslagerorte.objects.all()

    context = {
        "profil": profil,
        "kids": kids,
        "schwerpunkte": schwerpunkte,
        'orte_json': json.dumps({
            'orte': schwerpunkte_data,
        }),
        "auslagerorte": auslagerorte,
        "schwerpunkte_u": schwerpunkte_u,
    }
    print(context)

    return HttpResponse(template.render(context, request))


@login_required
def kitchen(request):
    template = loader.get_template('kitchen.html')
    current_user = request.user
    if not current_user.is_authenticated:
        # Redirect to the login page if not authenticated
        return redirect('login')
    profil = Profil.objects.get(user=current_user)
    active_turnus = profil.turnus
    team = Profil.objects.filter(turnus=active_turnus)
    kids = Kinder.objects.filter(turnus=active_turnus)
    schwerpunkte = Schwerpunkte.objects.filter(
        schwerpunktzeit__turnus=active_turnus)
    print("Schwerpunkte:", schwerpunkte)
    auslagerorte = Auslagerorte.objects.all()

    meal_types = ["breakfast", "lunch", "dinner"]
    meal_counts = {}

    for swp in schwerpunkte:
        week = swp.schwerpunktzeit.woche
        dauer = swp.schwerpunktzeit.dauer

        if week not in meal_counts:
            meal_counts[week] = {
                day: {
                    "breakfast": {"box": [], "budo": [], "warm": [], "kochportionen": 0},
                    "lunch": {"box": [], "budo": [], "warm": [], "kochportionen": 0},
                    "dinner": {"box": [], "budo": [], "warm": [], "kochportionen": 0}
                }
                for day in range(1, dauer + 1)
            }

        for meal in swp.meals.all():
            if meal.day <= dauer:
                kids_count = meal.get_kids_count()
                if meal.meal_choice:  # Check if meal.meal_choice is not empty
                    meal_counts[week][meal.day][meal.meal_type][meal.meal_choice].append(
                        f"{swp.swp_name} ({kids_count})")
                    if meal.meal_choice in ["budo", "warm"]:
                        meal_counts[week][meal.day][meal.meal_type]["kochportionen"] += kids_count

    # Format the meal counts data for the template
    formatted_meal_counts = {}
    for week, week_data in meal_counts.items():
        formatted_meal_counts[week] = {}
        for day, meals in week_data.items():
            formatted_meal_counts[week][day] = {
                meal_type: {
                    'box': meals[meal_type].get('box', []),
                    'budo': meals[meal_type].get('budo', []),
                    'warm': meals[meal_type].get('warm', []),
                    'kochportionen': meals[meal_type].get('kochportionen', 0)
                }
                for meal_type in meal_types
            }

    print("Formatted Meal Counts:", formatted_meal_counts)  # Debugging statement
    context = {
        "profil": profil,
        "schwerpunkte": schwerpunkte,
        "auslagerorte": auslagerorte,
        "meal_counts": formatted_meal_counts,
        "kids": kids,
        "team": team,
        "meal_types": meal_types,
    }
    return HttpResponse(template.render(context, request))


@login_required
def download_updated_excel(request):
    current_user = request.user
    profil = Profil.objects.get(user=current_user)
    active_turnus = profil.turnus

    if not active_turnus:
        return HttpResponse("No active turnus found.", status=404)

    file_path = os.path.join(
        settings.MEDIA_ROOT, f"Aufenthaltsdoku_{active_turnus}_ID{active_turnus.id}.xlsx")

    # Call the function to update the Excel file
    update_excel_file(file_path, active_turnus)

    # Serve the file as a download
    response = FileResponse(
        open(file_path, 'rb'), as_attachment=True, filename=os.path.basename(file_path))
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'

    # Delete the file after serving it
    def delete_file():
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file: {e}")

    response.close = delete_file

    return response


@login_required
def swp_einteilung(request, week):
    current_user = request.user
    profil = Profil.objects.get(user=current_user)
    active_turnus = profil.turnus
    schwerpunktzeit = Schwerpunktzeit.objects.get(
        turnus=active_turnus, woche=f"w{week}")

    kids = models.Kinder.objects.filter(turnus=active_turnus).prefetch_related(
        Prefetch('schwerpunkt_wahl',
                 queryset=SchwerpunktWahl.objects.filter(
                     schwerpunktzeit=schwerpunktzeit),
                 to_attr='wahl')
    ).prefetch_related(
        Prefetch('schwerpunkte',
                 queryset=Schwerpunkte.objects.filter(
                     schwerpunktzeit__woche=f"w{week}"),
                 to_attr='schwerpunkt')
    )

    schwerpunkte = Schwerpunkte.objects.filter(
        schwerpunktzeit__turnus=active_turnus, schwerpunktzeit__woche=f"w{week}")
    auslagerorte = Auslagerorte.objects.all()

    # Count kids not grouped yet
    ungrouped_count = sum(1 for kid in kids if not kid.schwerpunkt)

    template = loader.get_template('swp-einteilung.html')
    context = {
        'kids': kids,
        'schwerpunkte': schwerpunkte,
        'auslagerorte': auslagerorte,
        'ungrouped_count': ungrouped_count,
        'week_number': week,
    }
    return HttpResponse(template.render(context, request))


@login_required
def swp_einteilung_w1(request):
    return swp_einteilung(request, 1)


@login_required
def swp_einteilung_w2(request):
    return swp_einteilung(request, 2)


@require_POST
@csrf_protect
def update_schwerpunkt_wahl(request):
    data = json.loads(request.body)
    kid_id = data.get('kid_id')
    swp_id = data.get('swp_id')
    choice_rank = data.get('choice_rank')

    try:
        kid = Kinder.objects.get(id=kid_id)
        schwerpunkt = Schwerpunkte.objects.get(id=swp_id)
        schwerpunktzeit = schwerpunkt.schwerpunktzeit

        schwerpunkt_wahl, created = SchwerpunktWahl.objects.get_or_create(
            kind=kid,
            schwerpunktzeit=schwerpunktzeit
        )

        if choice_rank is not None:
            if choice_rank == '1':
                # Remove any existing schwerpunkt for this week
                kid.schwerpunkte.remove(
                    *kid.schwerpunkte.filter(schwerpunktzeit=schwerpunktzeit))

                schwerpunkt_wahl.erste_wahl = schwerpunkt
                kid.schwerpunkte.add(schwerpunkt)
            elif choice_rank == '2':
                schwerpunkt_wahl.zweite_wahl = schwerpunkt
            elif choice_rank == '3':
                schwerpunkt_wahl.dritte_wahl = schwerpunkt
        else:
            # Only update the assigned schwerpunkt without changing ranks
            kid.schwerpunkte.remove(
                *kid.schwerpunkte.filter(schwerpunktzeit=schwerpunktzeit))
            kid.schwerpunkte.add(schwerpunkt)

        schwerpunkt_wahl.save()

        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@require_POST
@csrf_protect
def update_freunde(request):
    data = json.loads(request.body)
    kid_id = data.get('kid_id')
    freunde = data.get('freunde')

    try:
        kid = Kinder.objects.get(id=kid_id)
        schwerpunkt_wahl = SchwerpunktWahl.objects.get(
            kind=kid, schwerpunktzeit__woche="w1")
        schwerpunkt_wahl.freunde = freunde
        schwerpunkt_wahl.save()
        return JsonResponse({'status': 'success'})
    except (Kinder.DoesNotExist, SchwerpunktWahl.DoesNotExist):
        return JsonResponse({'status': 'error', 'message': 'Kid or SchwerpunktWahl not found'})


@login_required
def happy_cleaning(request):
    # Get the current turnus (you might need to adjust this based on how you store the current turnus)
    current_turnus = request.user.profil.turnus

    # Query kids from the current turnus
    kids = Kinder.objects.filter(turnus=current_turnus)

    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="happy_cleaning.csv"'

    # Create the CSV writer
    writer = csv.writer(response)
    writer.writerow(['ID', 'Kindername'])

    # Write data rows
    for kid in kids:
        writer.writerow([kid.id, f"{kid.kid_vorname} {kid.kid_nachname}"])

    return response


@login_required
def kindergesamtzahl(request):
    current_user = request.user
    profil = Profil.objects.get(user=current_user)
    active_turnus = profil.turnus
    checked_in_count = Kinder.objects.filter(
        turnus=active_turnus, anwesend=True).count()
    total_kids = Kinder.objects.filter(turnus=active_turnus).count()
    context = {
        'checked_in_count': checked_in_count,
        'total_kids': total_kids,
    }
    return render(request, 'kindergesamtzahl.html', context)
