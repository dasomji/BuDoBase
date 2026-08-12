"""The sole outbound HTTP gateway for Google Maps services."""

import logging
from urllib.parse import urlsplit

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

SHORT_LINK_HOSTS = frozenset({"maps.app.goo.gl", "app.goo.gl", "goo.gl", "g.co"})
_EXPANSION_TIMEOUT_SECONDS = 5
_GEOCODING_TIMEOUT_SECONDS = 8


def expand_short_link(url):
    """Read exactly one redirect from an allowlisted Google short-link host."""
    try:
        parsed = urlsplit(url)
    except (TypeError, ValueError):
        return None
    hostname = (parsed.hostname or "").lower().rstrip(".")
    try:
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme != "https"
        or hostname not in SHORT_LINK_HOSTS
        or port not in {None, 443}
    ):
        logger.warning("Rejected non-allowlisted Google Maps short link")
        return None

    try:
        response = requests.get(
            url,
            allow_redirects=False,
            timeout=_EXPANSION_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("Google Maps short-link request failed")
        return None

    if response.status_code not in {301, 302, 303, 307, 308}:
        return None
    return response.headers.get("Location")


def reverse_geocode(latitude, longitude):
    """Return normalized address values from Google's Geocoding API."""
    api_key = settings.GOOGLE_MAPS_API_KEY
    if not api_key:
        logger.info("Skipping Google reverse geocoding: GOOGLE_MAPS_API_KEY is unset")
        return None

    try:
        response = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"latlng": f"{latitude},{longitude}", "key": api_key},
            timeout=_GEOCODING_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as error:
        # The request URL contains the API key, so never log the exception or
        # response URL here.
        logger.warning(
            "Google reverse-geocoding request failed (%s)",
            type(error).__name__,
        )
        return None

    if payload.get("status") != "OK" or not payload.get("results"):
        logger.warning(
            "Google reverse geocoding returned status %s",
            payload.get("status"),
        )
        return None

    components = payload["results"][0].get("address_components", [])
    by_type = {
        component_type: component.get("long_name", "")
        for component in components
        for component_type in component.get("types", [])
    }
    route = by_type.get("route", "")
    street_number = by_type.get("street_number", "")
    street = " ".join(part for part in (route, street_number) if part)
    city = next(
        (
            by_type.get(component_type)
            for component_type in (
                "locality",
                "postal_town",
                "administrative_area_level_2",
                "sublocality",
            )
            if by_type.get(component_type)
        ),
        "",
    )
    return {
        "street": street,
        "city": city,
        "state": by_type.get("administrative_area_level_1", ""),
        "postal_code": by_type.get("postal_code", ""),
        "country": by_type.get("country", ""),
    }
