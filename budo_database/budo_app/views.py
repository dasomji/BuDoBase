from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader
from budo_database.settings import MEDIA_ROOT
from .excelProcessor import process_excel
from . import models
import pandas as pd
import os

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
