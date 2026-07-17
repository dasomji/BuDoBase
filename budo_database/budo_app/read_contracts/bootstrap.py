from django.contrib import messages
from django.middleware.csrf import get_token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from budo_app.models import Auslagerorte, Kinder, Profil, Schwerpunkte


def _queued_messages(request):
    return [
        {"text": str(message), "tags": message.tags}
        for message in messages.get_messages(request._request)
    ]


def _permissions(user):
    return {
        "change_kids": user.has_perm("budo_app.change_kinder"),
        "change_focuses": user.has_perm("budo_app.change_schwerpunkte"),
        "change_places": user.has_perm("budo_app.change_auslagerorte"),
    }


def _search_index(turnus):
    if turnus is None:
        return {"kids": [], "focuses": [], "places": []}

    kids = [
        {
            "id": item["id"],
            "full_name": f'{item["kid_vorname"]} {item["kid_nachname"]}'.strip(),
            "present": item["anwesend"],
        }
        for item in Kinder.objects.filter(turnus=turnus)
        .values("id", "kid_vorname", "kid_nachname", "anwesend")
        .order_by("kid_vorname", "kid_nachname")
    ]
    focuses = [
        {"id": item["id"], "name": item["swp_name"]}
        for item in Schwerpunkte.objects.filter(schwerpunktzeit__turnus=turnus)
        .values("id", "swp_name")
        .order_by("swp_name")
    ]
    places = list(Auslagerorte.objects.values("id", "name").order_by("name"))
    return {"kids": kids, "focuses": focuses, "places": places}


@api_view(["GET"])
@permission_classes([AllowAny])
def bootstrap(request):
    """Return public shell state and the minimal active-Turnus search index."""
    payload = {
        "authenticated": request.user.is_authenticated,
        "csrf_token": get_token(request),
        "messages": _queued_messages(request),
    }
    if not request.user.is_authenticated:
        return Response(payload)

    try:
        profile = Profil.objects.select_related("user", "turnus").get(
            user=request.user,
        )
    except Profil.DoesNotExist:
        profile = None

    turnus = profile.turnus if profile else None
    payload.update(
        {
            "profile": (
                {
                    "id": profile.id,
                    "username": profile.user.username,
                    "rufname": profile.rufname,
                }
                if profile
                else None
            ),
            "turnus": (
                {
                    "id": turnus.id,
                    "label": str(turnus),
                    "number": turnus.turnus_nr,
                    "start": turnus.turnus_beginn.isoformat(),
                    "end": turnus.get_turnus_ende().isoformat(),
                }
                if turnus
                else None
            ),
            "permissions": _permissions(request.user),
            "search_index": _search_index(turnus),
        }
    )
    return Response(payload)
