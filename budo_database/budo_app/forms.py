from datetime import datetime
from django.forms import ModelForm, Form
from .models import Kinder, Notizen, Turnus
from django import forms
from django.contrib.auth.models import User
import datetime


class NotizForm(forms.ModelForm):
    class Meta:
        model = Notizen
        fields = ['notiz']

        widgets = {
            "notiz": forms.TextInput(attrs={'class': 'w3-input'})
        }


class CheckInForm(forms.ModelForm):

    class Meta:
        today = datetime.date.today().strftime('%Y-%m-%d')
        model = Kinder
        fields = ['check_in_date', 'ausweis', 'e_card', 'einverstaendnis_erklaerung',
                  'taschengeld']

        widgets = {
            'check_in_date': forms.DateInput(attrs={'type': 'date', 'class': 'w3-input', "value": f"{today}"}),
            'ausweis': forms.CheckboxInput(attrs={'class': 'w3-check w3-margin-left'}),
            'e_card': forms.CheckboxInput(attrs={'class': 'w3-check w3-margin-left'}),
            'einverstaendnis_erklaerung': forms.CheckboxInput(attrs={'class': 'w3-check w3-margin-left'}),
            'taschengeld': forms.TextInput(attrs={'class': 'w3-input'})
        }
        labels = {'einverstaendnis_erklaerung': "Einverständniserklärung"}


class UploadForm(forms.ModelForm):
    class Meta:
        model = Turnus
        fields = ['turnus_nr', 'turnus_beginn', 'uploadedFile']
        labels = {"turnus_nr": "Turnus Nummer",
                  "turnus_beginn": "Beginn des Turnus", "uploadedFile": "Excel-File"}
