from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_GET
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .location_services import refresh_all_auslagerorte_travel_times
from .react_views import render_react_page


@login_required
@require_GET
def admin_settings_page(request):
    if not request.user.is_staff:
        raise PermissionDenied("Admin settings access denied.")
    return render_react_page(request)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def recalculate_travel_times(request):
    updated = refresh_all_auslagerorte_travel_times()
    return Response({"updated": updated})
