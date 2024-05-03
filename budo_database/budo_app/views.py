from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template import loader
from datetime import datetime
from django.contrib import messages
from . import models
from .models import Kinder, Notizen
from .forms import NotizForm, CheckInForm, UploadForm, CheckOutForm
from copy import deepcopy


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


# def check_in_list(request, id):
#     kinder_instance = Kinder.objects.get(pk=id)
#     this_kid = models.Kinder.objects.get(id=id)
#     notizen = models.Notizen.objects.all()
#     kids = models.Kinder.objects.all()
#     today = datetime.today().strftime('%Y-%m-%d')
#     today_time = datetime.today().strftime('%d.%m.@%H:%M')
#     current_user = request.user
#     context = {
#         'today_date': today,
#         'this_kid': this_kid,
#         'kids': kids,
#         'notizen': notizen,
#         "current_user": current_user,
#     }

#     if request.method == 'GET':
#         form = CheckInForm()
#         return render(request, 'check_in_list.html', context)

#     elif request.method == 'POST':
#         form = CheckInForm(request.POST, user=request.user)
#         if form.is_valid():
#             this_kid = form.save(commit=False)
#             # Assuming you are using Django's built-in authentication
#             this_kid.save()
#             messages.success(
#                 request, f'{this_kid.kid_vorname} {this_kid.kid_nachname} erfolgreich eingecheckt.')
#             return redirect('check_in_all', id=id)

#     return render(request, 'check_in_list.html', context)

# def testing(request):
#     age_ordered = models.Kinder.objects.all().order_by('kid_alter').values()
#     length = len(models.Kinder.objects.all())
#     template = loader.get_template('testing.html')
#     context = {
#         "kids": age_ordered,
#         "kid_totalnumbers": length,
#     }
#     return HttpResponse(template.render(context, request))


# def budo_family_overview(request):
#     kids = models.Kinder.objects.all().order_by('kid_vorname')
#     familien = kids.values_list('budo_family', flat=True).distinct()
#     familiensizes = {}
#     for familie in familien:
#         family_kids = kids.filter(budo_family=familie)
#         familiensizes[f'{familie}'] = {
#             'name': f'{familie}',
#             'size': family_kids.count(),
#             'kids': list(family_kids)
#         }

#     context = {
#         'kids': kids,
#         "familien": familiensizes,

#     }
#     return render(request, 'budo_familien.html', context)


# def budo_family(request, budo_family):
#     family = budo_family
#     kids = models.Kinder.objects.filter(
#         budo_family=budo_family).order_by('kid_vorname')
#     template = loader.get_template('kids_list.html')
#     context = {
#         'kids': kids,
#         'family': family,
#     }
#     return HttpResponse(template.render(context, request))
