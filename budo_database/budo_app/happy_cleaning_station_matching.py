"""Authoritative station-name similarity used by copy previews."""

import re
import unicodedata


_UMLAUTS = str.maketrans({
    "ä": "ae",
    "ö": "oe",
    "ü": "ue",
    "ß": "ss",
})


def normalize_station_name(value):
    """Return a comparison form with German umlauts and separators unified."""
    normalized = unicodedata.normalize("NFC", value).casefold().translate(_UMLAUTS)
    return " ".join(re.sub(r"[^\w]+", " ", normalized, flags=re.UNICODE).split())


def station_names_are_similar(left, right):
    """Match equality or full-word containment of the shorter normalized name."""
    left_normalized = normalize_station_name(left)
    right_normalized = normalize_station_name(right)
    if not left_normalized or not right_normalized:
        return False
    if left_normalized == right_normalized:
        return True
    shorter, longer = sorted(
        (left_normalized, right_normalized),
        key=lambda item: (len(item), item),
    )
    return re.search(
        rf"(?<!\w){re.escape(shorter)}(?!\w)",
        longer,
        flags=re.UNICODE,
    ) is not None
