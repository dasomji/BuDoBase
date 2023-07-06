from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader
from datetime import datetime
from . import models

from .excelProcessor import process_excel

# Create your views here.


def budo_app(request):
    template = loader.get_template('myfirst.html')
    return HttpResponse(template.render())


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
