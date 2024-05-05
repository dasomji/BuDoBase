from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template import loader
from django.urls import reverse_lazy
from django.forms import modelformset_factory
from datetime import datetime
from django.contrib import messages
from . import models
from .models import Kinder, Notizen, Schwerpunkte, Meal, Profil
from django.views.generic.edit import CreateView, UpdateView
from .forms import NotizForm, CheckInForm, UploadForm, CheckOutForm, MealChoiceForm
from copy import deepcopy
from itertools import groupby


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


class SchwerpunkteUpdate(UpdateView):
    model = Schwerpunkte
    fields = ['swp_name', 'ort', 'betreuende', 'beschreibung',
              'schwerpunktzeit', 'auslagern', 'geplante_abreise', 'geplante_ankunft']
    template_name = "schwerpunkt.html"
    success_url = reverse_lazy('swp-dashboard')

    def form_valid(self, form):
        messages.success(self.request, "Profil upgedatet!")
        return super(SchwerpunkteUpdate, self).form_valid(form)


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
