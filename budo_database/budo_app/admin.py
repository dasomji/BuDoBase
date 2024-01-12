from django.contrib import admin
from .models import Kinder, Turnus, Schwerpunkte, Auslagerorte, Notizen, Document

# Register your models here.

admin.site.register(Kinder)
admin.site.register(Turnus)
admin.site.register(Schwerpunkte)
admin.site.register(Auslagerorte)
admin.site.register(Notizen)
admin.site.register(Document)
