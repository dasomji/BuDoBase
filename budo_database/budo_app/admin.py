from django.contrib import admin
from .models import Kinder, Turnus, Schwerpunkte, Auslagerorte, Notizen, Document, Profil, Meal, Schwerpunktzeit


class NotizenAdmin(admin.ModelAdmin):
    list_display = ("notiz", "kids_name", "added_by", "date_added")
    readonly_fields = ('date_added',)


class TurnusAdmin(admin.ModelAdmin):
    list_display = ("__str__", "turnus_beginn", "get_turnus_ende")
    readonly_fields = ('dateTimeOfUpload', "get_turnus_ende")
# Register your models here.


class ProfilAdmin(admin.ModelAdmin):
    list_display = ("__str__", 'rolle', 'get_food', 'allergien')


class MealInline(admin.TabularInline):
    model = Meal
    extra = 0  # Number of extra forms to display


class SchwerpunkteAdmin(admin.ModelAdmin):
    list_display = ("__str__", "ort", "display_betreuende",
                    "schwerpunktzeit", "auslagern")
    inlines = [MealInline]

    def display_betreuende(self, obj):
        return ", ".join([str(betreuer) for betreuer in obj.betreuende.all()])
    display_betreuende.short_description = 'Betreuende'


admin.site.register(Kinder)
admin.site.register(Turnus, TurnusAdmin)
admin.site.register(Auslagerorte)
admin.site.register(Notizen, NotizenAdmin)
admin.site.register(Document)
admin.site.register(Profil, ProfilAdmin)
admin.site.register(Schwerpunkte, SchwerpunkteAdmin)
admin.site.register(Meal)
admin.site.register(Schwerpunktzeit)
