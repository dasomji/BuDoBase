from django.contrib import admin
from .models import Kinder, Turnus, Schwerpunkte, Auslagerorte, Document

# Register your models here.

admin.site.register(Kinder)
admin.site.register(Turnus)
admin.site.register(Schwerpunkte)
admin.site.register(Auslagerorte)
admin.site.register(Document)
