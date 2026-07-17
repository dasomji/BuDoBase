from datetime import datetime
from django.conf import settings
from django.forms import ModelForm, Form
from .models import Kinder, Notizen, Turnus, Profil, Schwerpunkte, Meal, Auslagerorte, AuslagerorteNotizen, AuslagerorteImage, Schwerpunktzeit, Geld, BetreuerinnenGeld
from django import forms
from django.contrib.auth.models import User
import datetime


class NotizForm(forms.ModelForm):
    class Meta:
        model = Notizen
        fields = ['notiz']

        widgets = {
            "notiz": forms.TextInput(attrs={'class': 'w3-input', 'placeholder': 'Notiz...'})
        }


class GeldForm(forms.ModelForm):
    amount = forms.FloatField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'w3-input',
            'placeholder': 'Taschengeld...',
            'min': '0',
            'step': '0.01',
        }),
    )

    class Meta:
        model = Geld
        fields = ['amount']


class CheckInForm(forms.ModelForm):

    class Meta:
        today = datetime.date.today().strftime('%Y-%m-%d')
        model = Kinder
        fields = ['check_in_date', 'ausweis',
                  'e_card', 'einverstaendnis_erklaerung']

        widgets = {
            'check_in_date': forms.DateInput(attrs={'type': 'date', 'class': '', "value": f"{today}"}),
            'ausweis': forms.CheckboxInput(attrs={'class': ''}),
            'e_card': forms.CheckboxInput(attrs={'class': ''}),
            'einverstaendnis_erklaerung': forms.CheckboxInput(attrs={'class': ''}),
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
        today = datetime.date.today().strftime('%Y-%m-%d')
        model = Turnus
        fields = ['turnus_nr', 'turnus_beginn', 'uploadedFile']
        labels = {"turnus_nr": "Turnus Nummer",
                  "turnus_beginn": "Beginn des Turnus", "uploadedFile": "Excel-File"}
        widgets = {
            'uploadedFile': forms.ClearableFileInput(attrs={'required': False}),
            'turnus_beginn': forms.DateInput(attrs={'type': 'date', 'class': '', "value": f"{today}"}),
        }


class ProfilForm(forms.ModelForm):
    class Meta:
        model = Profil
        fields = ['allergien', 'rolle', 'essen', 'telefonnummer']
        labels = {'allergien': "Allergien", 'rolle': "Rolle", 'essen': "Essen"}


class SchwerpunktForm(forms.ModelForm):
    def __init__(self, *args, turnus=None, **kwargs):
        super().__init__(*args, **kwargs)
        if turnus is None:
            self.fields['betreuende'].queryset = Profil.objects.none()
            self.fields['schwerpunktzeit'].queryset = Schwerpunktzeit.objects.none()
            return
        self.fields['betreuende'].queryset = Profil.objects.filter(
            turnus=turnus,
        ).order_by('rufname', 'id')
        self.fields['schwerpunktzeit'].queryset = (
            Schwerpunktzeit.objects.filter(turnus=turnus)
            .order_by('woche', 'id')
        )

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
        fields = ['name', 'strasse', 'ort', 'bundesland', 'postleitzahl', 'land',
                  'maps_link', 'beschreibung', 'maps_link_parkspot', ]


class AuslagerNotizForm(forms.ModelForm):
    class Meta:
        model = AuslagerorteNotizen
        fields = ['notiz']

        widgets = {
            "notiz": forms.TextInput(attrs={'class': 'w3-input', 'placeholder': 'Kommentar...'})
        }


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "widget",
            MultipleFileInput(attrs={"accept": "image/*"}),
        )
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        files = list(data) if isinstance(data, (list, tuple)) else [data]
        files = [uploaded_file for uploaded_file in files if uploaded_file]

        if not files:
            super().clean(None, initial)
            return []

        if len(files) > settings.LOCATION_IMAGE_MAX_FILES:
            raise forms.ValidationError(
                "Es können höchstens %(limit)s Bilder gleichzeitig hochgeladen werden.",
                code="too_many_images",
                params={"limit": settings.LOCATION_IMAGE_MAX_FILES},
            )

        total_size = sum(uploaded_file.size for uploaded_file in files)
        if total_size > settings.LOCATION_IMAGE_MAX_TOTAL_SIZE:
            raise forms.ValidationError(
                "Die Bilder dürfen zusammen höchstens %(limit)s MB groß sein.",
                code="images_too_large",
                params={
                    "limit": settings.LOCATION_IMAGE_MAX_TOTAL_SIZE // (1024 * 1024),
                },
            )

        cleaned_files = []
        for uploaded_file in files:
            if uploaded_file.size > settings.LOCATION_IMAGE_MAX_FILE_SIZE:
                raise forms.ValidationError(
                    "Ein Bild darf höchstens %(limit)s MB groß sein.",
                    code="image_too_large",
                    params={
                        "limit": settings.LOCATION_IMAGE_MAX_FILE_SIZE // (1024 * 1024),
                    },
                )

            cleaned_file = super().clean(uploaded_file, initial)
            width, height = cleaned_file.image.size
            if width * height > settings.LOCATION_IMAGE_MAX_PIXELS:
                raise forms.ValidationError(
                    "Ein Bild darf höchstens %(limit)s Megapixel haben.",
                    code="too_many_pixels",
                    params={
                        "limit": settings.LOCATION_IMAGE_MAX_PIXELS // 1_000_000,
                    },
                )
            cleaned_files.append(cleaned_file)

        return cleaned_files


class AuslagerorteImageForm(forms.Form):
    images = MultipleImageField(
        label="Bilder auswählen",
        required=True,
    )


class MealChoiceForm(forms.ModelForm):
    class Meta:
        model = Meal
        fields = ('meal_choice',)


# Form for uploading a CSV file to update the spezialfamilien for all kids in the current turnus


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField()


class BetreuerinnenGeldForm(forms.ModelForm):
    class Meta:
        model = BetreuerinnenGeld
        fields = ['amount', 'what']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'w3-input', 'placeholder': 'Betrag in €', 'step': '0.01'}),
            'what': forms.TextInput(attrs={'class': 'w3-input', 'placeholder': 'Beschreibung'})
        }


class BirthdayNotizForm(forms.ModelForm):
    class Meta:
        model = Notizen
        fields = ['notiz']
        widgets = {
            "notiz": forms.TextInput(attrs={
                'class': 'w3-input',
                'placeholder': 'Geburtstagskorrektur...',
                'id': 'birthday-notiz-input'
            })
        }
