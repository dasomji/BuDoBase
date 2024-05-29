from datetime import datetime
from django.forms import ModelForm, Form
from .models import Kinder, Notizen, Turnus, Profil, Schwerpunkte, Meal, Auslagerorte, Schwerpunktzeit
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
            'check_in_date': forms.DateInput(attrs={'type': 'date', 'class': '', "value": f"{today}"}),
            'ausweis': forms.CheckboxInput(attrs={'class': ''}),
            'e_card': forms.CheckboxInput(attrs={'class': ''}),
            'einverstaendnis_erklaerung': forms.CheckboxInput(attrs={'class': ''}),
            'taschengeld': forms.TextInput(attrs={'class': ''})
        }
        labels = {'einverstaendnis_erklaerung': "Einverständniserklärung"}


class CheckOutForm(forms.ModelForm):
    class Meta:
        today = datetime.date.today().strftime('%Y-%m-%d')
        model = Kinder
        fields = ['early_abreise_date']
        widgets = {'early_abreise_date': forms.DateInput(
            attrs={'type': 'date', 'class': 'w3-input', "value": f"{today}"})}

        labels = {"early_abreise_date": "Abreisedatum"}


class UploadForm(forms.ModelForm):
    class Meta:
        model = Turnus
        fields = ['turnus_nr', 'turnus_beginn', 'uploadedFile']
        labels = {"turnus_nr": "Turnus Nummer",
                  "turnus_beginn": "Beginn des Turnus", "uploadedFile": "Excel-File"}


class ProfilForm(forms.ModelForm):
    class Meta:
        model = Profil
        fields = ['allergien', 'rolle', 'essen', 'telefonnummer']
        labels = {'allergien': "Allergien", 'rolle': "Rolle", 'essen': "Essen"}


class SchwerpunktForm(forms.ModelForm):
    class Meta:
        model = Schwerpunkte
        fields = ['swp_name', 'ort', 'betreuende', 'beschreibung',
                  'schwerpunktzeit', 'auslagern', 'geplante_abreise', 'geplante_ankunft']
        widgets = {
            'betreuende': forms.CheckboxSelectMultiple,
            'schwerpunktzeit': forms.Select(choices=Schwerpunktzeit.WOCHEN_AUSWAHL)
        }


class AuslagerForm(forms.ModelForm):
    class Meta:
        model = Auslagerorte
        fields = ['name', 'strasse', 'ort', 'bundesland', 'postleitzahl', 'land', 'koordinaten',
                  'maps_link', 'beschreibung', 'maps_link_parkspot', 'koordinaten_parkspot', ]


class MealChoiceForm(forms.ModelForm):
    class Meta:
        model = Meal
        fields = ('meal_choice',)
