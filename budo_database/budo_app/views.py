from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader
from datetime import datetime
from . import models

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
    context = {
        "today_date": today,
        'Kinder': this_kid,
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


def budo_family_dash(request):
    kids = models.Kinder.objects.all()
    familien = models.Kinder.BUDO_FAMILIES
    familiensizes = {}
    for familie in familien:
        familiensizes[f'{familie[1]}'] = len(
            kids.filter(budo_family=familie[1]))
    template = loader.get_template('budo_familien.html')
    context = {
        'kids': kids,
        "familien": familiensizes,

    }
    return HttpResponse(template.render(context, request))


def budo_family(request, budo_family):
    family = budo_family
    kids = models.Kinder.objects.filter(
        budo_family=budo_family).order_by('kid_vorname')
    template = loader.get_template('kids_list.html')
    context = {
        'kids': kids,
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


def postprocess(request):
    postprocessing()
