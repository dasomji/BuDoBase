from django import forms
from django.utils.html import format_html
from django.contrib import admin
from django.template.defaultfilters import filesizeformat
from .models import Kinder, Turnus, Schwerpunkte, Auslagerorte, AuslagerorteImage, AuslagerorteNotizen, Notizen, Document, Profil, Meal, Schwerpunktzeit, SchwerpunktWahl, SpezialFamilien


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
    list_display = ("__str__", "turnus")
    form = KinderAdminForm
    list_select_related = ('turnus', 'spezial_familien')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('turnus', 'spezial_familien')


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


class AuslagerorteNotizenAdmin(admin.ModelAdmin):
    list_display = ("notiz", "auslagerort", "added_by", "date_added")
    readonly_fields = ('date_added',)


class AuslagerorteImageAdmin(admin.ModelAdmin):
    list_display = ("image", "auslagerort", "file_size")

    def file_size(self, obj):
        if obj.image and hasattr(obj.image, 'size'):
            return filesizeformat(obj.image.size)
        return "N/A"
    file_size.short_description = "File Size"


class AuslagerorteNotizenInline(admin.TabularInline):
    model = AuslagerorteNotizen
    extra = 1


class AuslagerorteImageInline(admin.TabularInline):
    model = AuslagerorteImage
    extra = 1
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 150px; max-width: 150px;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Image Preview'


class AuslagerorteAdmin(admin.ModelAdmin):
    list_display = ("__str__", "get_notizen_count", "get_images_count")
    inlines = [AuslagerorteNotizenInline, AuslagerorteImageInline]

    def get_notizen_count(self, obj):
        return obj.auslagernotizen.count()
    get_notizen_count.short_description = 'Notizen'

    def get_images_count(self, obj):
        return obj.images.count()
    get_images_count.short_description = 'Bilder'


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
                    "schwerpunktzeit", "get_turnus", "auslagern", "get_kids_count")
    inlines = [KinderInline, MealInline]
    list_select_related = ('ort', 'schwerpunktzeit')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('ort', 'schwerpunktzeit').prefetch_related('betreuende', 'swp_kinder')

    def display_betreuende(self, obj):
        return ", ".join([str(betreuer) for betreuer in obj.betreuende.all()])
    display_betreuende.short_description = 'Betreuende'

    def get_turnus(self, obj):
        return obj.get_turnus()
    get_turnus.short_description = 'Turnus'

    def get_kids_count(self, obj):
        return obj.swp_kinder.count()
    get_kids_count.short_description = 'Kinder'


class KinderInlineForSpezialFamilien(admin.TabularInline):
    model = Kinder
    extra = 0
    verbose_name = "Kind"
    verbose_name_plural = "Kinder"
    readonly_fields = ('kid_vorname', 'kid_nachname')
    fields = ('kid_vorname', 'kid_nachname')

    def kid_name(self, obj):
        return f"{obj.kid_vorname} {obj.kid_nachname}"


class SpezialFamilienAdmin(admin.ModelAdmin):
    list_display = ("__str__", "turnus", "get_kids_count")
    inlines = [KinderInlineForSpezialFamilien]

    def get_kids_count(self, obj):
        return obj.kinder.count()
    get_kids_count.short_description = 'Kinder'


class SchwerpunktzeitAdmin(admin.ModelAdmin):
    list_display = ("__str__", "display_swps")

    def display_swps(self, obj):
        return ", ".join([str(swp) for swp in obj.swp.all()])
    display_swps.short_description = 'Schwerpunkte'


admin.site.register(Kinder, KinderAdmin)
admin.site.register(Turnus, TurnusAdmin)
admin.site.register(Auslagerorte, AuslagerorteAdmin)
admin.site.register(AuslagerorteImage, AuslagerorteImageAdmin)
admin.site.register(AuslagerorteNotizen, AuslagerorteNotizenAdmin)
admin.site.register(Notizen, NotizenAdmin)
admin.site.register(Document)
admin.site.register(Profil, ProfilAdmin)
admin.site.register(Schwerpunkte, SchwerpunkteAdmin)
admin.site.register(Meal)
admin.site.register(Schwerpunktzeit, SchwerpunktzeitAdmin)
admin.site.register(SchwerpunktWahl)
admin.site.register(SpezialFamilien, SpezialFamilienAdmin)
