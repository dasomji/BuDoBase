from django.contrib import admin
from .models import Kinder, Turnus, Schwerpunkte, Auslagerorte, Notizen, Document


class NotizenAdmin(admin.ModelAdmin):
    readonly_fields = ('date_added',)

# Register your models here.


admin.site.register(Kinder)
admin.site.register(Turnus)
admin.site.register(Schwerpunkte)
admin.site.register(Auslagerorte)
admin.site.register(Notizen, NotizenAdmin)
admin.site.register(Document)
