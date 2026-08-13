from django.core.exceptions import PermissionDenied
from django.db.models import Prefetch
from django.db.models.functions import Lower
from django.http import Http404
from django.shortcuts import get_object_or_404

from budo_app.models import (
    Auslagerorte,
    AuslagerorteImage,
    AuslagerorteNotizen,
    Tag,
)
from budo_app.read_contracts.common import (
    active_turnus_id,
    required_query_integer,
    serialize_note,
)
from budo_app.tag_icons import TAG_ICON_CHOICES


def _has_active_turnus(request):
    return active_turnus_id(request) is not None


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


def _tag_catalog():
    return list(
        Tag.objects.order_by(Lower("name"), "id").values("id", "name", "icon")
    )


def _ordered_tags(place):
    tags = list(place.route_tags)
    if place.primary_tag_id:
        tags.sort(key=lambda tag: (tag.id != place.primary_tag_id, tag.name.casefold(), tag.id))
    return tags


def places_list(request):
    if not _has_active_turnus(request):
        return {"places": [], "available_tags": [], "tag_catalog": []}
    images = AuslagerorteImage.objects.only(
        "id", "auslagerort_id", "notiz_id", "image",
    ).order_by("id")
    notes = AuslagerorteNotizen.objects.select_related("added_by").prefetch_related(
        Prefetch("images", queryset=images, to_attr="route_images"),
    ).order_by("date_added", "id")
    places = Auslagerorte.objects.select_related("primary_tag").prefetch_related(
        Prefetch(
            "images",
            queryset=images.filter(notiz_id__isnull=True),
            to_attr="route_images",
        ),
        Prefetch("auslagernotizen", queryset=notes, to_attr="route_notes"),
        _tag_prefetch(),
    ).order_by("name", "id")
    place_list = list(places)
    available_tags = sorted(
        {tag.name for place in place_list for tag in place.route_tags},
        key=str.casefold,
    )
    return {
        "places": [_detail_place(place) for place in place_list],
        "available_tags": available_tags,
        "tag_catalog": _tag_catalog(),
    }


def _detail_place(place):
    ordered_tags = _ordered_tags(place)
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
        "gallery_images": [
            {
                "id": image.id,
                "url": image.image.url,
                "alt": f"Bild von {place.name}",
                "comment_text": None,
            }
            for image in place.route_images
            if image.image
        ] + [
            {
                "id": image.id,
                "url": image.image.url,
                "alt": f"Kommentarbild zu {place.name}",
                "comment_text": note.notiz,
            }
            for note in place.route_notes
            for image in note.route_images
            if image.image
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
        "tags": [tag.name for tag in ordered_tags],
        "marker_icon": place.primary_tag.icon if place.primary_tag else "map-pin",
    }


def place_detail(request):
    _require_active_turnus(request)
    images = AuslagerorteImage.objects.only(
        "id",
        "auslagerort_id",
        "notiz_id",
        "image",
    ).order_by("id")
    notes = AuslagerorteNotizen.objects.select_related("added_by").prefetch_related(
        Prefetch("images", queryset=images, to_attr="route_images"),
    ).order_by(
        "date_added",
        "id",
    )
    queryset = Auslagerorte.objects.select_related("primary_tag").prefetch_related(
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
    return {
        "places": [],
        "available_tags": _available_tag_names(),
        "tag_catalog": _tag_catalog(),
    }


def _form_place(place):
    ordered_tags = _ordered_tags(place)
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
        "contact": place.kontakt,
        "parking_link": place.maps_link_parkspot,
        "tags": [tag.name for tag in ordered_tags],
    }


def place_update(request):
    _require_active_turnus(request)
    place = get_object_or_404(
        Auslagerorte.objects.select_related("primary_tag").only(
            "id",
            "name",
            "strasse",
            "ort",
            "bundesland",
            "postleitzahl",
            "land",
            "maps_link",
            "beschreibung",
            "kontakt",
            "maps_link_parkspot",
            "primary_tag_id",
            "primary_tag__icon",
        ).prefetch_related(_tag_prefetch()),
        id=required_query_integer(request),
    )
    return {
        "places": [_form_place(place)],
        "available_tags": _available_tag_names(),
        "tag_catalog": _tag_catalog(),
    }


def tag_settings(request):
    if not request.user.has_perm("budo_app.change_tag"):
        raise PermissionDenied("Tag settings access denied.")
    places = Auslagerorte.objects.only("id", "name").order_by(Lower("name"), "id")
    tags = Tag.objects.prefetch_related(
        Prefetch("auslagerorte", queryset=places, to_attr="tagged_places"),
    ).order_by(Lower("name"), "id")
    return {
        "tags": [
            {
                "id": tag.id,
                "name": tag.name,
                "icon": tag.icon,
                "places": [
                    {"id": place.id, "name": place.name}
                    for place in tag.tagged_places
                ],
            }
            for tag in tags
        ],
        "icon_choices": [
            {"value": value, "label": label}
            for value, label in TAG_ICON_CHOICES
        ],
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
    "place-tag-settings": tag_settings,
}
