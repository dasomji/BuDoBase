from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from budo_app.models import HappyCleaning
from budo_app.react_views import render_react_page


def _event_in_active_turnus_or_404(request, event_id):
    return get_object_or_404(
        HappyCleaning.objects.only("id"),
        id=event_id,
        turnus_id=request.user.profil.turnus_id,
    )


@require_GET
@login_required
def assignment_page(request, event_id):
    _event_in_active_turnus_or_404(request, event_id)
    return render_react_page(request)


@require_GET
@login_required
def print_number_page(request):
    if request.user.profil.turnus_id is None:
        raise Http404
    return render_react_page(request)


@require_GET
@login_required
def event_print_number_page(request, event_id):
    _event_in_active_turnus_or_404(request, event_id)
    return HttpResponseRedirect("/happy-cleaning/print/")
