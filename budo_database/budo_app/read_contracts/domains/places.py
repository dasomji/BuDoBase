from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404

from budo_app.models import (
    Auslagerorte,
    AuslagerorteImage,
    AuslagerorteNotizen,
    Profil,
)


def _has_active_turnus(request):
    return Profil.objects.filter(
        user_id=request.user.id,
        turnus_id__isnull=False,
    ).exists()


def _require_active_turnus(request):
    if not _has_active_turnus(request):
        raise Http404


def _list_place(place):
    return {
        "id": place["id"],
        "name": place["name"],
        "coordinates": place["koordinaten"],
        "maps_link": place["maps_link"],
        "parking_link": place["maps_link_parkspot"],
    }


def places_list(request):
    if not _has_active_turnus(request):
        return {"places": []}
    places = Auslagerorte.objects.values(
        "id",
        "name",
        "koordinaten",
        "maps_link",
        "maps_link_parkspot",
    ).order_by("name", "id")
    return {"places": [_list_place(place) for place in places]}


def _datetime(value):
    return value.isoformat() if value else None


def _detail_place(place):
    return {
        "id": place.id,
        "name": place.name,
        "street": place.strasse,
        "city": place.ort,
        "state": place.bundesland,
        "postal_code": place.postleitzahl,
        "country": place.land,
        "coordinates": place.koordinaten,
        "maps_link": place.maps_link,
        "description": place.beschreibung,
        "contact": place.kontakt,
        "parking_link": place.maps_link_parkspot,
        "parking_coordinates": place.koordinaten_parkspot,
        "images": [
            image.image.url for image in place.route_images if image.image
        ],
        "notes": [
            {
                "id": note.id,
                "text": note.notiz or "",
                "author": note.added_by.username,
                "date": _datetime(note.date_added),
                "day": (
                    note.date_added.strftime("%d.%m.")
                    if note.date_added
                    else ""
                ),
            }
            for note in place.route_notes
        ],
    }


def _place_id(request):
    place_id = request.query_params.get("id")
    if not place_id or not str(place_id).isdigit():
        raise Http404
    return int(place_id)


def place_detail(request):
    _require_active_turnus(request)
    images = AuslagerorteImage.objects.only(
        "id",
        "auslagerort_id",
        "image",
    ).order_by("id")
    notes = AuslagerorteNotizen.objects.select_related("added_by").order_by(
        "date_added",
        "id",
    )
    queryset = Auslagerorte.objects.prefetch_related(
        Prefetch("images", queryset=images, to_attr="route_images"),
        Prefetch(
            "auslagernotizen",
            queryset=notes,
            to_attr="route_notes",
        ),
    )
    place = get_object_or_404(queryset, id=_place_id(request))
    return {"places": [_detail_place(place)]}


def place_create(request):
    return {"places": []}


def _form_place(place):
    return {
        "id": place["id"],
        "name": place["name"],
        "street": place["strasse"],
        "city": place["ort"],
        "state": place["bundesland"],
        "postal_code": place["postleitzahl"],
        "country": place["land"],
        "maps_link": place["maps_link"],
        "description": place["beschreibung"],
        "parking_link": place["maps_link_parkspot"],
    }


def place_update(request):
    _require_active_turnus(request)
    place = get_object_or_404(
        Auslagerorte.objects.values(
            "id",
            "name",
            "strasse",
            "ort",
            "bundesland",
            "postleitzahl",
            "land",
            "maps_link",
            "beschreibung",
            "maps_link_parkspot",
        ),
        id=_place_id(request),
    )
    return {"places": [_form_place(place)]}


def place_images(request):
    _require_active_turnus(request)
    place = get_object_or_404(
        Auslagerorte.objects.values("id", "name"),
        id=_place_id(request),
    )
    return {"places": [place]}


CONTRACTS = {
    "place-create": place_create,
    "place-detail": place_detail,
    "place-images": place_images,
    "place-update": place_update,
    "places-list": places_list,
}
