from django.contrib import admin
from .models import Kinder, Turnus, SchwerpunktOne, SchwerpunktTwo, Document

# Register your models here.

admin.site.register(Kinder)
admin.site.register(Turnus)
admin.site.register(SchwerpunktOne)
admin.site.register(SchwerpunktTwo)
admin.site.register(Document)
