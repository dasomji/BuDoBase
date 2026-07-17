from django.http import Http404

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


def serialize_note(note):
    return {
        "id": note.id,
        "text": note.notiz or "",
        "date": serialize_datetime(note.date_added),
        "day": note.date_added.strftime("%d.%m.") if note.date_added else "",
        "author": note.added_by.username,
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
