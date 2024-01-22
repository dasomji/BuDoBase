from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.template import loader
from datetime import datetime
from django.contrib import messages
from . import models
from .models import Kinder
from .forms import CheckInForm

from .excelProcessor import process_excel, postprocessing

# Create your views here.


def budo_app(request):
    template = loader.get_template('main.html')
    kids = models.Kinder.objects.all()
    context = {
        "kids": kids
    }
    return HttpResponse(template.render(context, request))


def uploadFile(request):
    if request.method == "POST":
        # Fetching the form data
        turnus_number = request.POST["turnus_nr"]
        turnus_jahr = request.POST["turnus_year"]
        uploadedFile = request.FILES["uploadedFile"]

        # Saving the information in the database
        turnus = models.Turnus(
            turnus_nr=int(turnus_number),
            turnus_year=int(turnus_jahr),
            uploadedFile=uploadedFile
        )
        turnus.save()
        process_excel()  # saves the data from excel to the database

    documents = models.Turnus.objects.all()

    return render(request, "upload-file.html", context={
        "files": documents
    })


def kids_list(request):
    kids = models.Kinder.objects.all().values()
    template = loader.get_template('kids_list.html')
    context = {
        'kids': kids,
    }
    return HttpResponse(template.render(context, request))


def kid_details(request, id):
    this_kid = models.Kinder.objects.get(id=id)
    template = loader.get_template('kids_data.html')
    today = datetime.today().strftime('%Y-%m-%d')
    notizen = this_kid.notizen.all()
    context = {
        "today_date": today,
        'Kinder': this_kid,
        "Notizen": notizen,
    }
    return HttpResponse(template.render(context, request))


def testing(request):
    age_ordered = models.Kinder.objects.all().order_by('kid_alter').values()
    length = len(models.Kinder.objects.all())
    template = loader.get_template('testing.html')
    context = {
        "kids": age_ordered,
        "kid_totalnumbers": length,
    }
    return HttpResponse(template.render(context, request))


def budo_family_overview(request):
    kids = models.Kinder.objects.all().order_by('kid_vorname')
    familien = kids.values_list('budo_family', flat=True).distinct()
    familiensizes = {}
    for familie in familien:
        family_kids = kids.filter(budo_family=familie)
        familiensizes[f'{familie}'] = {
            'name': f'{familie}',
            'size': family_kids.count(),
            'kids': list(family_kids)
        }

    context = {
        'kids': kids,
        "familien": familiensizes,

    }
    return render(request, 'budo_familien.html', context)


def budo_family(request, budo_family):
    family = budo_family
    kids = models.Kinder.objects.filter(
        budo_family=budo_family).order_by('kid_vorname')
    template = loader.get_template('kids_list.html')
    context = {
        'kids': kids,
        'family': family,
    }
    return HttpResponse(template.render(context, request))


def check_in(request, id):
    this_kid = models.Kinder.objects.get(id=id)
    template = loader.get_template('check_in.html')
    today = datetime.today().strftime('%Y-%m-%d')
    today_time = datetime.today().strftime('%d.%m.@%H:%M')
    context = {
        "today_date": today,
        'Kinder': this_kid,
    }

    if request.method == "POST":
        if this_kid.anwesend == False:
            check_in_date = request.POST.get("check_in_date")
            ausweis = request.POST.get("ausweis")
            e_card = request.POST.get("e-card")
            einverstaendnis = request.POST.get("einverstaendnis")
            taschengeld = request.POST.get("taschengeld")
            anmerkung = request.POST.get("neue_anmerkung")

            this_kid.check_in_date = check_in_date
            this_kid.ausweis = ausweis
            this_kid.e_card = e_card
            this_kid.einverstaendnis_erklaerung = einverstaendnis
            this_kid.taschengeld = taschengeld
            this_kid.anmerkung_team += f'<br>@Checkin/{today_time}: {anmerkung}'
            this_kid.anwesend = True
        else:
            early_check_out = request.POST.get("early_check_out")
            check_out_date = request.POST.get("check_out_date")
            documents_returned = request.POST.get("documents_returned")
            abholer = request.POST.get("abholer")
            reason_abreise = request.POST.get("reason_abreise")
            taschengeld_out = request.POST.get("taschengeld_out")
            anmerkung = request.POST.get("neue_anmerkung")

            this_kid.anwesend = False
            if early_check_out == True:
                this_kid.early_abreise_date = check_out_date
                this_kid.early_abreise_abholer = abholer
                this_kid.early_abreise_reason = reason_abreise
                this_kid.anmerkung_team += f'<br>{taschengeld_out}€ retourniert'

            if documents_returned == True:
                this_kid.ausweis = False
                this_kid.e_card = False

            this_kid.anmerkung_team += f'<br>@Checkout/{today_time}: {anmerkung}'

        this_kid.save()

    print(request.POST.get("e-card"))

    return HttpResponse(template.render(context, request))


def check_in_list(request, id):
    kinder_instance = Kinder.objects.get(pk=id)
    this_kid = models.Kinder.objects.get(id=id)
    notizen = models.Notizen.objects.all()
    kids = models.Kinder.objects.all()
    today = datetime.today().strftime('%Y-%m-%d')
    today_time = datetime.today().strftime('%d.%m.@%H:%M')
    context = {
        'today_date': today,
        'this_kid': this_kid,
        'kids': kids,
        'notizen': notizen
    }

    if request.method == 'GET':
        form = CheckInForm()
        return render(request, 'check_in_list.html', context)

    elif request.method == 'POST':
        form = CheckInForm(request.POST)
        if form.is_valid():
            this_kid = form.save(commit=False)
            # Assuming you are using Django's built-in authentication
            notizen.added_by = request.user
            this_kid.save()
            messages.success(
                request, f'{this_kid.kid_vorname} {this_kid.kid_nachname} erfolgreich eingecheckt.')
            return redirect('check_in_all', id=id)

    return render(request, 'check_in_list.html', context)


def check_in_list_older(request, id):
    this_kid = models.Kinder.objects.get(id=id)
    notizen = models.Notizen.objects.all()
    kids = models.Kinder.objects.all()
    template = loader.get_template('check_in_list.html')
    today = datetime.today().strftime('%Y-%m-%d')
    today_time = datetime.today().strftime('%d.%m.@%H:%M')
    context = {
        "today_date": today,
        'this_kid': this_kid,
        'kids': kids,
        'notizen': notizen
    }

    if request.method == "POST":
        if this_kid.anwesend == False:
            check_in_date = request.POST.get("check_in_date")
            ausweis = request.POST.get("ausweis")
            e_card = request.POST.get("e-card")
            einverstaendnis = request.POST.get("einverstaendnis")
            taschengeld = request.POST.get("taschengeld")
            # anmerkung = request.POST.get("neue_anmerkung")
            neue_notiz = request.POST.get("neue_notiz")

            this_kid.check_in_date = check_in_date
            this_kid.ausweis = ausweis
            this_kid.e_card = e_card
            this_kid.einverstaendnis_erklaerung = einverstaendnis
            this_kid.taschengeld = taschengeld

            if neue_notiz != "":
                notizen.notiz = neue_notiz
                notizen.kinder = this_kid.kid_index
                notizen.added_by = request.user

            # this_kid.anmerkung_team += f'<br>@Checkin/{today_time}: {anmerkung}'
            this_kid.anwesend = True
        else:
            early_check_out = request.POST.get("early_check_out")
            check_out_date = request.POST.get("check_out_date")
            documents_returned = request.POST.get("documents_returned")
            abholer = request.POST.get("abholer")
            reason_abreise = request.POST.get("reason_abreise")
            taschengeld_out = request.POST.get("taschengeld_out")
            neue_notiz = request.POST.get("neue_notiz")
            # anmerkung = request.POST.get("neue_anmerkung")

            this_kid.anwesend = False
            if early_check_out == True:
                this_kid.early_abreise_date = check_out_date
                this_kid.early_abreise_abholer = abholer
                this_kid.early_abreise_reason = reason_abreise
                this_kid.anmerkung_team += f'<br>{taschengeld_out}€ retourniert'

            if documents_returned == True:
                this_kid.ausweis = False
                this_kid.e_card = False

            # this_kid.anmerkung_team += f'<br>@Checkout/{today_time}: {anmerkung}'

        this_kid.save()
        notizen.save()

    print(request.POST.get("e-card"))

    return HttpResponse(template.render(context, request))


def check_in_list_old(request, id):
    this_kid = models.Kinder.objects.get(id=id)
    kids = models.Kinder.objects.all()
    if request.method == 'GET':

        context = {'form': CheckInForm(instance=this_kid), 'kids': kids}
        return render(request, 'check_in_list.html', context)

    elif request.method == 'POST':
        form = CheckInForm(request.POST, instance=this_kid)
        if form.is_valid():
            form.save()
            messages.success(
                request, 'The post has been updated successfully.')
            return redirect('posts')
        else:
            messages.error(request, 'Please correct the following errors:')
            return render(request, '/all_kids', {'form': form})


def postprocess(request):
    postprocessing()
