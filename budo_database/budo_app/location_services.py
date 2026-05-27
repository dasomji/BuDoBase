import logging
import re

import requests

logger = logging.getLogger(__name__)


def extract_coordinates_from_maps_link(url):
    try:
        response = requests.get(url, allow_redirects=True, timeout=5)
        response.raise_for_status()
        match = re.search(r'3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', response.url)
        if match:
            lat, lon = map(float, match.groups())
            return lat, lon
    except requests.RequestException:
        logger.exception("Error extracting coordinates from maps link")

    return None, None


def update_auslagerorte_coordinates(auslagerort):
    if auslagerort.maps_link:
        lat, lon = extract_coordinates_from_maps_link(auslagerort.maps_link)
        if lat and lon:
            auslagerort.koordinaten = f"{lat},{lon}"

    if auslagerort.maps_link_parkspot:
        lat, lon = extract_coordinates_from_maps_link(
            auslagerort.maps_link_parkspot)
        if lat and lon:
            auslagerort.koordinaten_parkspot = f"{lat},{lon}"

    return auslagerort
