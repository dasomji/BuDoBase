from django.http import Http404
from django.urls import reverse

from budo_app.models import Profil


def active_turnus_id(request):
    """Return the request user's selected Turnus without loading its profile."""
    return (
        Profil.objects.filter(user_id=request.user.id)
        .values_list("turnus_id", flat=True)
        .first()
    )


def require_active_turnus_id(request):
    turnus_id = active_turnus_id(request)
    if turnus_id is None:
        raise Http404
    return turnus_id


def required_query_integer(request, name="id", *, digits_only=True):
    """Read a required integer query parameter or respond 404."""
    value = request.query_params.get(name)
    if digits_only:
        if not value or not str(value).isdigit():
            raise Http404
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        raise Http404 from None


def kid_full_name(first_name, last_name):
    return f"{first_name or ''} {last_name or ''}".strip()


def serialize_money(value):
    return round(float(value or 0), 2)


def serialize_datetime(value):
    return value.isoformat() if value else None


def _serialize_text_entry(entry, text):
    return {
        "id": entry.id,
        "text": text or "",
        "date": serialize_datetime(entry.date_added),
        "day": entry.date_added.strftime("%d.%m.") if entry.date_added else "",
        "author": entry.added_by.username,
    }


def serialize_photos(entry, child_name, kind):
    photos = getattr(entry, "route_photos", ())
    if kind == "notes":
        label, entry_label = "Notizfoto", "Notiz"
    else:
        label, entry_label = "EH-Foto", "EH-Eintrag"
    entry_suffix = (
        f", {entry_label} vom {entry.date_added.strftime('%d.%m.%Y %H:%M')}"
        if entry.date_added
        else ""
    )
    return [
        {
            "id": photo.id,
            "url": reverse("attachment-media", args=(kind, photo.id)),
            "width": photo.width,
            "height": photo.height,
            "alt": f"{label} {ordinal} von {child_name}{entry_suffix}",
        }
        for ordinal, photo in enumerate(photos, start=1)
    ]


def serialize_note(note, child_name=""):
    serialized = _serialize_text_entry(note, note.notiz)
    if hasattr(note, "route_photos"):
        serialized["photos"] = serialize_photos(note, child_name, "notes")
    return serialized


def serialize_first_aid_photos(entry, child_name):
    return serialize_photos(entry, child_name, "first-aid")


def serialize_first_aid_entry(entry, child_name):
    return {
        **_serialize_text_entry(entry, entry.beschreibung),
        "photos": serialize_first_aid_photos(entry, child_name),
    }


def serialize_transaction(transaction):
    return {
        "id": transaction.id,
        "amount": serialize_money(transaction.amount),
        "date": serialize_datetime(transaction.date_added),
        "day": (
            transaction.date_added.strftime("%d.%m.")
            if transaction.date_added
            else ""
        ),
        "author": transaction.added_by.username,
    }


def serialize_utc_datetime(value):
    serialized = serialize_datetime(value)
    return serialized.replace("+00:00", "Z") if serialized else None
