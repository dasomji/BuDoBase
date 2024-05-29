from django import forms
from django.contrib import admin
from .models import Kinder, Turnus, Schwerpunkte, Auslagerorte, Notizen, Document, Profil, Meal, Schwerpunktzeit


class KinderAdminForm(forms.ModelForm):
    schwerpunkt_w1 = forms.ModelChoiceField(
        queryset=Schwerpunkte.objects.filter(schwerpunktzeit__woche='w1'),
        required=False,
    )
    schwerpunkt_w2 = forms.ModelChoiceField(
        queryset=Schwerpunkte.objects.filter(schwerpunktzeit__woche='w2'),
        required=False,
    )

    class Meta:
        model = Kinder
        fields = '__all__'
        exclude = ['schwerpunkte']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['schwerpunkt_w1'].initial = self.instance.schwerpunkte.filter(
                schwerpunktzeit__woche='w1').first()
            self.fields['schwerpunkt_w2'].initial = self.instance.schwerpunkte.filter(
                schwerpunktzeit__woche='w2').first()

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Save the instance first
        if commit:
            instance.save()

        # Clear the existing Schwerpunkte
        instance.schwerpunkte.clear()

        # Save the selected Schwerpunkte
        if self.cleaned_data.get('schwerpunkt_w1'):
            instance.schwerpunkte.add(self.cleaned_data.get('schwerpunkt_w1'))
        if self.cleaned_data.get('schwerpunkt_w2'):
            instance.schwerpunkte.add(self.cleaned_data.get('schwerpunkt_w2'))

        # Save the instance again to update the ManyToManyField
        if commit:
            instance.save()

        return instance


class KinderAdmin(admin.ModelAdmin):
    form = KinderAdminForm


class KinderInline(admin.TabularInline):
    model = Kinder.schwerpunkte.through
    extra = 1
    verbose_name = "Kind"
    verbose_name_plural = "Kinder"

    def kid_name(self, obj):
        kid = obj.kinder
        return f"{kid.kid_vorname} {kid.kid_nachname}"


class NotizenAdmin(admin.ModelAdmin):
    list_display = ("notiz", "kids_name", "added_by", "date_added")
    readonly_fields = ('date_added',)


class TurnusAdmin(admin.ModelAdmin):
    list_display = ("__str__", "turnus_beginn", "get_turnus_ende", "id")
    readonly_fields = ('dateTimeOfUpload', "get_turnus_ende")
# Register your models here.


class ProfilAdmin(admin.ModelAdmin):
    list_display = ("__str__", 'rolle', 'get_food', 'allergien', 'turnus')


class MealInline(admin.TabularInline):
    model = Meal
    extra = 0  # Number of extra forms to display


class SwpInline(admin.TabularInline):
    model = Schwerpunkte
    extra = 0


class SchwerpunkteAdmin(admin.ModelAdmin):
    list_display = ("__str__", "ort", "display_betreuende",
                    "schwerpunktzeit", "auslagern")
    inlines = [KinderInline, MealInline]

    def display_betreuende(self, obj):
        return ", ".join([str(betreuer) for betreuer in obj.betreuende.all()])
    display_betreuende.short_description = 'Betreuende'


class SchwerpunktzeitAdmin(admin.ModelAdmin):
    list_display = ("__str__", "display_swps")

    def display_swps(self, obj):
        return ", ".join([str(swp) for swp in obj.swp.all()])
    display_swps.short_description = 'Schwerpunkte'


admin.site.register(Kinder, KinderAdmin)
admin.site.register(Turnus, TurnusAdmin)
admin.site.register(Auslagerorte)
admin.site.register(Notizen, NotizenAdmin)
admin.site.register(Document)
admin.site.register(Profil, ProfilAdmin)
admin.site.register(Schwerpunkte, SchwerpunkteAdmin)
admin.site.register(Meal)
admin.site.register(Schwerpunktzeit, SchwerpunktzeitAdmin)
