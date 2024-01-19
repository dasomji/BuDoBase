from django.forms import ModelForm
from .models import Kinder
from django import forms


class CheckInForm(ModelForm):
    class Meta:
        model = Kinder
        fields = ['check_in_date', 'ausweis', 'einverstaendnis_erklaerung',
                  'taschengeld', 'late_anreise']


class CheckInForm(forms.Form):
    pass


class CheckOutEarly(ModelForm):

    class Meta:
        model = Kinder
        fields = ['early_abreise_date',
                  'early_abreise_reason', 'early_abreise_abholer']


class CheckOutTemporary(ModelForm):
    class Meta:
        model = Kinder
        fields = ['wo']


# <p><label for="check_in_date">Check-In Datum</label><input type="date" id="check_in_date" value="{{today_date}}"></p>
# <p><label for="ausweis">Ausweis</label><input type="checkbox" id="ausweis"></p>
# <p><label for="e-card">E-Card</label><input type="checkbox" id="e-card"></p>
# <p><label for="covid">Covid Test-Erlaubnis</label><input type="checkbox" name="Covid" id="covid"></p>
# <p><label for="einverstaendnis">Einverständniserklärung</label><input type="checkbox" name="" id="einverstaendnis"></p>
# <p><label for="taschengeld">Taschengeld </label><input type="text" name="" id="taschengeld"></p>
