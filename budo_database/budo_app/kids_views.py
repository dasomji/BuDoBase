import logging
import os
from copy import deepcopy
from datetime import datetime

import toml
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template import loader
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from . import models
from .forms import CheckInForm, CheckOutForm, GeldForm, NotizForm
from .models import Auslagerorte, Kinder, Profil, Schwerpunkte
from .utils import (
    cache_user_profile,
    get_active_kid_or_404,
    get_turnus_data_optimized,
    parse_json_body,
    safe_get_object_or_404,
)

logger = logging.getLogger(__name__)

info_file_path = os.path.join(settings.BASE_DIR, "info.toml")
info = toml.load(info_file_path)


@login_required
@cache_user_profile
def kids_list(request):
    if not request.user_profile:
        messages.error(
            request, "Profile not found. Please contact an administrator.")
        return redirect('dashboard')

    turnus_data = get_turnus_data_optimized(request.active_turnus)
    template = loader.get_template('kids_list.html')
    context = {
        'kids': turnus_data['kids'],
        'schwerpunkte': turnus_data['schwerpunkte'],
        'auslagerorte': turnus_data['auslagerorte'],
    }
    return HttpResponse(template.render(context, request))


@login_required
@cache_user_profile
def budo_families(request):
    if not request.user_profile:
        messages.error(
            request, "Profile not found. Please contact an administrator.")
        return redirect('dashboard')

    turnus_data = get_turnus_data_optimized(request.active_turnus)
    kids = turnus_data['kids']

    familien = {}
    for kid in kids:
        family_name = kid.budo_family
        if family_name not in familien:
            familien[family_name] = {
                'name': family_name,
                'kids': []
            }
        familien[family_name]['kids'].append(kid)

    context = {
        'familien': familien,
        'schwerpunkte': turnus_data['schwerpunkte'],
        'auslagerorte': turnus_data['auslagerorte'],
        'kids': kids,
    }
    return render(request, 'budo_familien.html', context)


@login_required
def spezial_familien(request):
    spezial_familien = {}
    profil = Profil.objects.get(user=request.user)
    active_turnus = profil.turnus
    kids = models.Kinder.objects.filter(
        turnus=active_turnus).order_by('kid_vorname')
    schwerpunkte = Schwerpunkte.objects.filter(
        schwerpunktzeit__turnus=active_turnus)
    auslagerorte = Auslagerorte.objects.all()
    for kid in kids:
        family_name = kid.spezial_familien.name if kid.spezial_familien else None
        if family_name:
            if family_name not in spezial_familien:
                spezial_familien[family_name] = {
                    'name': family_name,
                    'kids': []
                }
            spezial_familien[family_name]['kids'].append(kid)

    context = {
        'spezial_familien': spezial_familien,
        'schwerpunkte': schwerpunkte,
        'auslagerorte': auslagerorte,
        'kids': kids,
    }
    return render(request, 'spezial_familien.html', context)


@login_required
def zugabreise(request):
    profil = Profil.objects.get(user=request.user)
    active_turnus = profil.turnus
    kids = models.Kinder.objects.filter(
        turnus=active_turnus).order_by('-zug_abreise', 'kid_vorname')
    schwerpunkte = Schwerpunkte.objects.filter(
        schwerpunktzeit__turnus=active_turnus)
    auslagerorte = Auslagerorte.objects.all()
    zugabreise_count = models.Kinder.get_zugabreise_count(
        turnus=active_turnus)
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
    profil = Profil.objects.get(user=request.user)
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


@login_required
@cache_user_profile
@csrf_protect
@require_POST
def toggle_zug_abreise(request):
    if not request.active_turnus:
        return JsonResponse({'status': 'error', 'message': 'No active turnus'}, status=400)

    kid_id = request.POST.get('id')
    kid = get_active_kid_or_404(request, kid_id)
    kid.zug_abreise = not kid.zug_abreise
    kid.save()

    zugabreise_count = Kinder.objects.filter(
        zug_abreise=True, turnus=request.active_turnus).count()

    return JsonResponse({'status': 'success', 'new_count': zugabreise_count})


@login_required
@cache_user_profile
@csrf_protect
@require_POST
def update_notiz_abreise(request):
    data = parse_json_body(request)
    if data is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    kid_id = data.get('id')
    new_notiz_abreise = data.get('notiz_abreise')

    kid = get_active_kid_or_404(request, kid_id)
    kid.notiz_abreise = new_notiz_abreise
    kid.save()
    return JsonResponse({'status': 'success'})


@login_required
@cache_user_profile
def kid_details(request, id):
    if not request.user_profile:
        messages.error(
            request, "Profile not found. Please contact an administrator.")
        return redirect('dashboard')

    this_kid = safe_get_object_or_404(
        models.Kinder, id=id, turnus=request.active_turnus)
    turnus_data = get_turnus_data_optimized(request.active_turnus)
    kids = turnus_data['kids']
    schwerpunkte = turnus_data['schwerpunkte']
    auslagerorte = turnus_data['auslagerorte']
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
                if request.POST.get("money_action") == "withdraw":
                    geld.amount = -abs(geld.amount)
                else:
                    geld.amount = abs(geld.amount)
                geld.kinder = this_kid
                geld.added_by = request.user
                geld.save()
            return redirect('kid_details', id=id)
        else:
            logger.debug("Geld form is not valid: %s", geld_form.errors)
    else:
        notiz_form = NotizForm()
        geld_form = GeldForm()
        context["notiz_form"] = notiz_form
        context["geld_form"] = geld_form

    return HttpResponse(template.render(context, request))


@login_required
@cache_user_profile
def check_in(request, id):
    if not request.user_profile:
        messages.error(
            request, "Profile not found. Please contact an administrator.")
        return redirect('dashboard')

    this_kid = safe_get_object_or_404(
        models.Kinder, id=id, turnus=request.active_turnus)
    original_kid = deepcopy(this_kid)
    kids = models.Kinder.objects.all().values()
    schwerpunkte = Schwerpunkte.objects.filter(
        schwerpunktzeit__turnus=request.active_turnus)
    auslagerorte = Auslagerorte.objects.all()
    template = loader.get_template('check_in.html')
    today = datetime.today().strftime('%Y-%m-%d')
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
        if check_in_form.is_valid() and notiz_form.is_valid() and geld_form.is_valid():
            this_kid = check_in_form.save(commit=False)
            this_kid.anwesend = True
            if this_kid.check_in_date.strftime("%Y-%m-%d") != this_kid.turnus.turnus_beginn.strftime("%Y-%m-%d"):
                this_kid.late_anreise = this_kid.check_in_date
                if original_kid.check_in_date is not None:
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
@cache_user_profile
def check_out(request, id):
    if not request.user_profile:
        messages.error(
            request, "Profile not found. Please contact an administrator.")
        return redirect('dashboard')

    this_kid = get_active_kid_or_404(request, id)
    kids = models.Kinder.objects.filter(turnus=request.active_turnus).values()
    schwerpunkte = Schwerpunkte.objects.filter(
        schwerpunktzeit__turnus=request.active_turnus)
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
    pocket_money_balance = this_kid.get_taschengeld_sum()

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
                geld.amount = -abs(geld.amount) if pocket_money_balance >= 0 else abs(geld.amount)
                geld.kinder = this_kid
                geld.added_by = request.user
                geld.save()
        if check_out_form.is_valid() and notiz_form.is_valid() and geld_form.is_valid():
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
        geld_form = GeldForm(initial={
            'amount': pocket_money_balance if pocket_money_balance > 0 else 0,
        })
        if pocket_money_balance >= 0:
            geld_form.fields['amount'].label = f"Taschengeld zurückgegeben (aktuell {pocket_money_balance:.2f} €)"
        else:
            geld_form.fields['amount'].label = f"Taschengeld eingezahlt (schuldet aktuell: {abs(pocket_money_balance):.2f} €)"
        context["check_out_form"] = check_out_form
        context["notiz_form"] = notiz_form
        context["geld_form"] = geld_form

    return HttpResponse(template.render(context, request))


@login_required
def serienbrief(request):
    profil = Profil.objects.get(user=request.user)
    active_turnus = profil.turnus
    kids = models.Kinder.objects.filter(
        turnus=active_turnus).order_by('kid_vorname')
    template = loader.get_template('serienbrief.html')
    context = {
        "kids": kids,
    }

    return HttpResponse(template.render(context, request))


@login_required
def murdergame(request):
    profil = Profil.objects.get(user=request.user)
    active_turnus = profil.turnus
    kids = models.Kinder.objects.filter(turnus=active_turnus, anwesend=True)
    team = models.Profil.objects.filter(turnus=active_turnus)
    template = loader.get_template('murdergame.html')
    context = {
        "kids": kids,
        "team": team,
    }

    return HttpResponse(template.render(context, request))
