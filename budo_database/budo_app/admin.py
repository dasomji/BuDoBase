from django.contrib import admin
from .models import Kinder, Turnus, Schwerpunkte, Auslagerorte, Notizen, Document


class NotizenAdmin(admin.ModelAdmin):
    list_display = ("notiz", "kids_name", "added_by", "date_added")
    readonly_fields = ('date_added',)


class TurnusAdmin(admin.ModelAdmin):
    list_display = ("__str__", "turnus_beginn")
    readonly_fields = ('dateTimeOfUpload',)
# Register your models here.


admin.site.register(Kinder)
admin.site.register(Turnus, TurnusAdmin)
admin.site.register(Schwerpunkte)
admin.site.register(Auslagerorte)
admin.site.register(Notizen, NotizenAdmin)
admin.site.register(Document)
