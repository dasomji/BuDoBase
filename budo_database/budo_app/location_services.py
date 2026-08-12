"""Google Maps location handling for Auslagerorte.

URL parsing stays pure and all outbound Google traffic is delegated to the
``google_maps_gateway`` module, which is also the single test seam.
"""

import logging
import math
import re
from urllib.parse import parse_qs, unquote_plus, urlsplit

from . import google_maps_gateway

logger = logging.getLogger(__name__)

_NUMBER = r"-?(?:\d+(?:\.\d*)?|\.\d+)"
_DATA_COORDINATES = re.compile(rf"!3d({_NUMBER})!4d({_NUMBER})")
_AT_COORDINATES = re.compile(rf"@({_NUMBER}),({_NUMBER})(?:,|/|$)")
_PAIR = re.compile(rf"^\s*({_NUMBER})\s*,\s*({_NUMBER})\s*$")
_SEARCH_PAIR = re.compile(rf"(?:^|/)search/({_NUMBER})[+, ]+({_NUMBER})(?:/|$)")
_GOOGLE_HOST = re.compile(
    r"^(?:(?:www|maps)\.)?google\.(?:com|at|de|ch|co\.uk|[a-z]{2})$",
    re.IGNORECASE,
)
_SHORT_LINK_HOSTS = frozenset({"maps.app.goo.gl", "app.goo.gl", "goo.gl", "g.co"})


def _validated_coordinates(latitude, longitude):
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(latitude) or not math.isfinite(longitude):
        return None
    if -90 <= latitude <= 90 and -180 <= longitude <= 180:
        return latitude, longitude
    return None


def parse_google_maps_coordinates(url):
    """Return coordinates embedded in a full Google Maps URL, without I/O."""
    if not url:
        return None

    try:
        parsed = urlsplit(url)
    except (TypeError, ValueError):
        return None
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme not in {"http", "https"} or not _GOOGLE_HOST.fullmatch(hostname):
        return None
    if not parsed.path.startswith("/maps") and not hostname.startswith("maps.google."):
        return None

    decoded_url = unquote_plus(url)
    data_pairs = _DATA_COORDINATES.findall(decoded_url)
    if data_pairs:
        return _validated_coordinates(*data_pairs[-1])

    match = _AT_COORDINATES.search(decoded_url)
    if match:
        return _validated_coordinates(*match.groups())

    query = parse_qs(parsed.query)
    for value in query.get("q", []):
        match = _PAIR.fullmatch(value)
        if match:
            return _validated_coordinates(*match.groups())

    match = _SEARCH_PAIR.search(unquote_plus(parsed.path))
    if match:
        return _validated_coordinates(*match.groups())
    return None


def _coordinates_for_link(url):
    coordinates = parse_google_maps_coordinates(url)
    if coordinates is not None:
        return coordinates

    try:
        hostname = (urlsplit(url).hostname or "").lower().rstrip(".")
    except (TypeError, ValueError):
        return None
    if hostname not in _SHORT_LINK_HOSTS:
        return None

    try:
        expanded_url = google_maps_gateway.expand_short_link(url)
    except Exception:
        logger.exception("Google Maps short-link expansion failed")
        return None
    return parse_google_maps_coordinates(expanded_url)


def _coordinate_string(coordinates):
    latitude, longitude = coordinates
    return f"{latitude},{longitude}"


def _stored_coordinates(value):
    match = _PAIR.fullmatch(value or "")
    if not match:
        return None
    return _validated_coordinates(*match.groups())


def update_auslagerorte_travel_times(auslagerort):
    """Update route estimates from BuDo, leaving failures as missing data."""
    destination = _stored_coordinates(auslagerort.koordinaten)
    auslagerort.driving_minutes = None
    auslagerort.walking_minutes = None
    if destination is None:
        return auslagerort

    if auslagerort.name == "BuDo":
        origin = destination
    else:
        from .models import Auslagerorte

        budo = (
            Auslagerorte.objects.filter(name="BuDo")
            .only("koordinaten")
            .order_by("id")
            .first()
        )
        origin = _stored_coordinates(budo.koordinaten) if budo else None
    if origin is None:
        logger.info(
            "Skipping travel-time lookup for %s: BuDo coordinates are unavailable",
            auslagerort.name,
        )
        return auslagerort

    failed = False
    for field_name, travel_mode in (
        ("driving_minutes", "DRIVE"),
        ("walking_minutes", "WALK"),
    ):
        try:
            duration = google_maps_gateway.route_duration_minutes(
                origin,
                destination,
                travel_mode,
            )
        except Exception as error:
            logger.warning(
                "Travel-time lookup failed for %s (%s): %s",
                auslagerort.name,
                travel_mode,
                error,
            )
            failed = True
            continue
        setattr(auslagerort, field_name, duration)
        failed = failed or duration is None

    if failed:
        getattr(auslagerort, "_location_warnings", []).append(
            "Die Reisezeiten vom BuDo konnten nicht vollständig ermittelt werden."
        )
    return auslagerort


def enrich_empty_address_fields(auslagerort, coordinates):
    """Reverse-geocode coordinates and fill only address fields still empty."""
    try:
        address = google_maps_gateway.reverse_geocode(*coordinates)
    except Exception:
        logger.exception("Google Maps reverse geocoding failed")
        return auslagerort
    if not address:
        return auslagerort

    field_mapping = {
        "strasse": "street",
        "ort": "city",
        "bundesland": "state",
        "postleitzahl": "postal_code",
        "land": "country",
    }
    for model_field, address_key in field_mapping.items():
        if not getattr(auslagerort, model_field) and address.get(address_key):
            setattr(auslagerort, model_field, address[address_key])
    return auslagerort


def update_auslagerorte_coordinates(auslagerort):
    """Apply changed Google Maps links to an Auslagerort before it is saved.

    Views may set the private ``_maps_link_changed`` flags from ModelForm's
    change tracking. New/legacy callers process both links by default.
    """
    main_changed = getattr(auslagerort, "_maps_link_changed", True)
    parking_changed = getattr(auslagerort, "_maps_link_parkspot_changed", True)
    warnings = []
    auslagerort._location_warnings = warnings

    if main_changed:
        previous_coordinates = auslagerort.koordinaten
        auslagerort.koordinaten = None
        if auslagerort.maps_link:
            coordinates = _coordinates_for_link(auslagerort.maps_link)
            if coordinates is None:
                warnings.append(
                    "Aus dem Google-Maps-Link konnten keine Koordinaten ermittelt werden."
                )
            else:
                auslagerort.koordinaten = _coordinate_string(coordinates)
                if getattr(auslagerort, "_enrich_address", True):
                    enrich_empty_address_fields(auslagerort, coordinates)

        if _stored_coordinates(previous_coordinates) != _stored_coordinates(
            auslagerort.koordinaten
        ):
            update_auslagerorte_travel_times(auslagerort)

    if parking_changed:
        auslagerort.koordinaten_parkspot = None
        if auslagerort.maps_link_parkspot:
            coordinates = _coordinates_for_link(auslagerort.maps_link_parkspot)
            if coordinates is None:
                warnings.append(
                    "Aus dem Google-Maps-Link für den Parkspot konnten keine "
                    "Koordinaten ermittelt werden."
                )
            else:
                auslagerort.koordinaten_parkspot = _coordinate_string(coordinates)

    auslagerort._location_warnings = warnings
    return auslagerort
