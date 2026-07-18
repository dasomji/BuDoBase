from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from budo_app.models import HappyCleaning


@require_GET
@login_required
def assignment_page(request, event_id):
    get_object_or_404(
        HappyCleaning.objects.only("id"),
        id=event_id,
        turnus_id=request.user.profil.turnus_id,
    )
    return HttpResponse("<html><body></body></html>")
