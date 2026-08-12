from django.db.models import Prefetch
from django.db.models.functions import Lower
from django.http import Http404
from django.shortcuts import get_object_or_404

from budo_app.models import (
    Auslagerorte,
    AuslagerorteImage,
    AuslagerorteNotizen,
    Profil,
    Tag,
)
from budo_app.read_contracts.common import (
    required_query_integer,
    serialize_note,
)


def _has_active_turnus(request):
    return Profil.objects.filter(
        user_id=request.user.id,
        turnus_id__isnull=False,
    ).exists()


def _require_active_turnus(request):
    if not _has_active_turnus(request):
        raise Http404


def _available_tag_names(*, in_use=False):
    tags = Tag.objects.all()
    if in_use:
        tags = tags.filter(auslagerorte__isnull=False).distinct()
    return list(tags.order_by(Lower("name"), "id").values_list("name", flat=True))


def _tag_prefetch():
    return Prefetch(
        "tags",
        queryset=Tag.objects.order_by(Lower("name"), "id"),
        to_attr="route_tags",
    )


def places_list(request):
    if not _has_active_turnus(request):
        return {"places": [], "available_tags": []}
    images = AuslagerorteImage.objects.only(
        "id", "auslagerort_id", "notiz_id", "image",
    ).order_by("id")
    notes = AuslagerorteNotizen.objects.select_related("added_by").prefetch_related(
        Prefetch("images", queryset=images, to_attr="route_images"),
    ).order_by("date_added", "id")
    places = Auslagerorte.objects.prefetch_related(
        Prefetch(
            "images",
            queryset=images.filter(notiz_id__isnull=True),
            to_attr="route_images",
        ),
        Prefetch("auslagernotizen", queryset=notes, to_attr="route_notes"),
        _tag_prefetch(),
    ).order_by("name", "id")
    return {
        "places": [_detail_place(place) for place in places],
        "available_tags": _available_tag_names(in_use=True),
    }


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
        "driving_minutes": place.driving_minutes,
        "walking_minutes": place.walking_minutes,
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
                **serialize_note(note),
                "photos": [
                    {
                        "id": image.id,
                        "url": image.image.url,
                        "alt": f"Kommentarbild zu {place.name}",
                    }
                    for image in note.route_images
                    if image.image
                ],
            }
            for note in place.route_notes
        ],
        "tags": [tag.name for tag in place.route_tags],
    }


def place_detail(request):
    _require_active_turnus(request)
    images = AuslagerorteImage.objects.only(
        "id",
        "auslagerort_id",
        "image",
    ).order_by("id")
    notes = AuslagerorteNotizen.objects.select_related("added_by").prefetch_related(
        Prefetch("images", queryset=images, to_attr="route_images"),
    ).order_by(
        "date_added",
        "id",
    )
    queryset = Auslagerorte.objects.prefetch_related(
        Prefetch(
            "images",
            queryset=images.filter(notiz_id__isnull=True),
            to_attr="route_images",
        ),
        Prefetch(
            "auslagernotizen",
            queryset=notes,
            to_attr="route_notes",
        ),
        _tag_prefetch(),
    )
    place = get_object_or_404(queryset, id=required_query_integer(request))
    return {"places": [_detail_place(place)]}


def place_create(request):
    return {"places": [], "available_tags": _available_tag_names()}


def _form_place(place):
    return {
        "id": place.id,
        "name": place.name,
        "street": place.strasse,
        "city": place.ort,
        "state": place.bundesland,
        "postal_code": place.postleitzahl,
        "country": place.land,
        "maps_link": place.maps_link,
        "description": place.beschreibung,
        "parking_link": place.maps_link_parkspot,
        "tags": [tag.name for tag in place.route_tags],
    }


def place_update(request):
    _require_active_turnus(request)
    place = get_object_or_404(
        Auslagerorte.objects.only(
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
        ).prefetch_related(_tag_prefetch()),
        id=required_query_integer(request),
    )
    return {
        "places": [_form_place(place)],
        "available_tags": _available_tag_names(),
    }


def place_images(request):
    _require_active_turnus(request)
    place = get_object_or_404(
        Auslagerorte.objects.values("id", "name"),
        id=required_query_integer(request),
    )
    return {"places": [place]}


CONTRACTS = {
    "place-create": place_create,
    "place-detail": place_detail,
    "place-images": place_images,
    "place-update": place_update,
    "places-list": places_list,
}
