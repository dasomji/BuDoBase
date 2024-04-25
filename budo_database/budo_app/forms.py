from django.forms import ModelForm, Form
from .models import Kinder, Notizen
from django import forms
from django.contrib.auth.models import User


class NeueNotiz(ModelForm):
    class Meta:
        model = Notizen
        fields = ['notiz']
        widgets = {
            'notiz': forms.TextInput(attrs={'class': 'w3-input'})
        }

    def form_valid(self, form):
        form.instance.added_by = self.request.user
        return super().form_valid(form)


# class NotizForm(Form):
#     notiz = forms.Textarea()

class NotizForm(forms.ModelForm):
    class Meta:
        model = Notizen
        fields = ['notiz']


class NeuerCheckIn(ModelForm):
    class Meta:
        model = Kinder
        fields = ['check_in_date', 'ausweis', 'e_card', 'einverstaendnis_erklaerung',
                  'taschengeld', 'late_anreise']
        widgets = {
            'check_in_date': forms.DateInput(attrs={'type': 'date', 'class': 'w3-input'}),
            'ausweis': forms.CheckboxInput(attrs={'class': 'w3-check w3-margin-left'}),
            'e_card': forms.CheckboxInput(attrs={'class': 'w3-check w3-margin-left'}),
            'einverstaendnis_erklaerung': forms.CheckboxInput(attrs={'class': 'w3-check w3-margin-left'}),
            'taschengeld': forms.TextInput(attrs={'class': 'w3-input'}),
            'neue_notiz': forms.TextInput(attrs={'class': 'w3-input'}),
        }


class CheckInForm(ModelForm):

    class Meta:
        model = Kinder
        fields = ['check_in_date', 'ausweis', 'e_card', 'einverstaendnis_erklaerung',
                  'taschengeld', 'late_anreise']
        widgets = {
            'check_in_date': forms.DateInput(attrs={'type': 'date', 'class': 'w3-input'}),
            'ausweis': forms.CheckboxInput(attrs={'class': 'w3-check w3-margin-left'}),
            'e_card': forms.CheckboxInput(attrs={'class': 'w3-check w3-margin-left'}),
            'einverstaendnis_erklaerung': forms.CheckboxInput(attrs={'class': 'w3-check w3-margin-left'}),
            'taschengeld': forms.TextInput(attrs={'class': 'w3-input'}),
            'neue_notiz': forms.TextInput(attrs={'class': 'w3-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(CheckInForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        kinder_instance = super().save(commit=False)
        current_user = self.user

        # Update fields of the Kinder instance
        kinder_instance.check_in_date = self.cleaned_data['check_in_date']
        kinder_instance.ausweis = self.cleaned_data['ausweis']
        kinder_instance.e_card = self.cleaned_data['e_card']
        kinder_instance.einverstaendnis_erklaerung = self.cleaned_data[
            'einverstaendnis_erklaerung']
        kinder_instance.taschengeld = self.cleaned_data['taschengeld']

        if commit:
            kinder_instance.save()  # Save the Kinder instance only if commit is True

            # Create a new Notizen instance associated with the Kinder instance
            notiz = Notizen(
                kinder=kinder_instance,
                notiz=self.cleaned_data['neue_notiz'],  # Corrected assignment
                added_by=current_user
            )
            notiz.save()

        # # Create a new Notizen instance associated with the Kinder instance
        # notiz = Notizen(
        #     kinder=kinder_instance,
        #     notiz=['neue_notiz'],
        #     added_by=current_user
        # )

        # kinder_instance.save()
        # notiz.save()

        return kinder_instance


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
