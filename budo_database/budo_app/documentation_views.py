from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET

from .react_views import render_react_page


@login_required
@require_GET
def documentation_page(request):
    return render_react_page(request)
