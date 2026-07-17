import base64
import binascii
import json
from datetime import datetime

from django.db.models import FloatField, Q, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework.exceptions import ValidationError

from budo_app.models import (
    Geld,
    Kinder,
    Notizen,
    Profil,
    Schwerpunkte,
)


# Both initial activity streams and every continuation page are capped here.
DASHBOARD_ACTIVITY_PAGE_SIZE = 20


def _money(value):
    return round(float(value or 0), 2)


def _datetime(value):
    return value.isoformat().replace("+00:00", "Z") if value else None


def _encode_cursor(item):
    payload = json.dumps(
        {"date": _datetime(item.date_added), "id": item.id},
        separators=(",", ":"),
    ).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_cursor(value):
    try:
        padded = value + ("=" * (-len(value) % 4))
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
        cursor_date = datetime.fromisoformat(payload["date"].replace("Z", "+00:00"))
        cursor_id = int(payload["id"])
        if cursor_id < 1 or cursor_date.tzinfo is None:
            raise ValueError
        return cursor_date, cursor_id
    except (
        AttributeError,
        binascii.Error,
        KeyError,
        TypeError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        raise ValidationError({"cursor": "Invalid dashboard activity cursor."})


def _activity_queryset(kind, turnus_id):
    model = Notizen if kind == "notes" else Geld
    return (
        model.objects.filter(kinder__turnus_id=turnus_id)
        .select_related("kinder", "added_by")
        .only(
            "id",
            "date_added",
            "added_by__username",
            "kinder_id",
            "kinder__kid_vorname",
            "kinder__kid_nachname",
            *(('notiz',) if kind == "notes" else ('amount',)),
        )
        .order_by("-date_added", "-id")
    )


def _activity_item(kind, item):
    common = {
        "id": item.id,
        "date": _datetime(item.date_added),
        "author": item.added_by.username,
        "kid_id": item.kinder_id,
        "kid": str(item.kinder),
    }
    if kind == "notes":
        return {**common, "text": item.notiz or ""}
    return {**common, "amount": _money(item.amount)}


def _activity_page(kind, turnus_id, cursor=None):
    if turnus_id is None:
        return {
            "items": [],
            "next_cursor": None,
            "has_more": False,
            "limit": DASHBOARD_ACTIVITY_PAGE_SIZE,
        }

    queryset = _activity_queryset(kind, turnus_id)
    if cursor:
        cursor_date, cursor_id = _decode_cursor(cursor)
        queryset = queryset.filter(
            Q(date_added__lt=cursor_date)
            | Q(date_added=cursor_date, id__lt=cursor_id)
        )
    page_items = list(queryset[: DASHBOARD_ACTIVITY_PAGE_SIZE + 1])
    has_more = len(page_items) > DASHBOARD_ACTIVITY_PAGE_SIZE
    page_items = page_items[:DASHBOARD_ACTIVITY_PAGE_SIZE]
    return {
        "items": [_activity_item(kind, item) for item in page_items],
        "next_cursor": (
            _encode_cursor(page_items[-1]) if has_more and page_items else None
        ),
        "has_more": has_more,
        "limit": DASHBOARD_ACTIVITY_PAGE_SIZE,
    }


def _profile_payload(profile, focus_ids):
    return {
        "id": profile.id,
        "email": profile.user.email,
        "phone": str(profile.telefonnummer),
        "allergies": profile.allergien,
        "coffee": profile.coffee,
        "role_display": profile.get_rolle(),
        "food_display": profile.get_food(),
        "focus_ids": focus_ids,
    }


def _kid_payload(kid):
    return {
        "id": kid.id,
        "full_name": str(kid),
        "present": kid.anwesend,
        "age": kid.get_alter(),
        "sex": kid.sex,
        "weeks": kid.turnus_dauer,
        "budo_experience": kid.budo_erfahrung,
        "birthday": kid.kid_birthday.isoformat() if kid.kid_birthday else None,
        "birthday_during_turnus": kid.is_birthday_during_turnus(),
        "food": kid.get_food(),
        "special_food": kid.get_clean_special_food(),
        "drugs": kid.get_clean_drugs(),
        "illness": kid.get_clean_illness(),
    }


def _empty_summary(profile):
    return {
        "profile": _profile_payload(profile, []),
        "team": [],
        "totals": {
            "kids": 0,
            "checked_in": 0,
            "train_arrival": 0,
            "train_departure": 0,
            "pocket_money": 0.0,
            "pocket_money_paid": 0.0,
            "team_money": 0.0,
        },
        "kids": [],
        "focuses": [],
    }


def build_dashboard_contract(request):
    profile = (
        Profil.objects.filter(user_id=request.user.id)
        .select_related("user")
        .first()
    )
    if profile is None:
        return {
            "profile": None,
            "team": [],
            "totals": {},
            "kids": [],
            "focuses": [],
            "activity": {
                "notes": _activity_page("notes", None),
                "transactions": _activity_page("transactions", None),
            },
        }

    turnus_id = profile.turnus_id
    activity_kind = request.query_params.get("activity")
    cursor = request.query_params.get("cursor")
    if activity_kind is not None:
        if activity_kind not in ("notes", "transactions"):
            raise ValidationError(
                {"activity": "Unknown dashboard activity stream."}
            )
        return {
            "activity": {
                activity_kind: _activity_page(activity_kind, turnus_id, cursor),
            }
        }
    if cursor is not None:
        raise ValidationError({"cursor": "An activity stream is required."})

    summary = _empty_summary(profile)
    if turnus_id is not None:
        focuses = list(
            Schwerpunkte.objects.filter(
                schwerpunktzeit__turnus_id=turnus_id,
                betreuende=profile,
            )
            .only("id", "swp_name")
            .order_by("schwerpunktzeit__woche", "swp_name", "id")
        )
        focus_ids = [focus.id for focus in focuses]
        team = list(
            Profil.objects.filter(turnus_id=turnus_id)
            .annotate(
                dashboard_money_total=Coalesce(
                    Sum("betreuerinnen_geld__amount"),
                    Value(0.0),
                    output_field=FloatField(),
                )
            )
            .only("id", "rufname", "essen", "allergien")
            .order_by("rufname", "id")
        )
        kids = list(
            Kinder.objects.filter(turnus_id=turnus_id)
            .select_related("turnus")
            .only(
                "id",
                "kid_vorname",
                "kid_nachname",
                "kid_birthday",
                "turnus_id",
                "turnus__turnus_beginn",
                "anwesend",
                "zug_anreise",
                "zug_abreise",
                "sex",
                "turnus_dauer",
                "budo_erfahrung",
                "vegetarisch",
                "special_food_description",
                "drugs",
                "illness",
            )
            .order_by("kid_vorname", "kid_nachname", "id")
        )
        money_totals = Geld.objects.filter(kinder__turnus_id=turnus_id).aggregate(
            total=Coalesce(Sum("amount"), Value(0.0), output_field=FloatField()),
            paid=Coalesce(
                Sum("amount", filter=Q(amount__gt=0)),
                Value(0.0),
                output_field=FloatField(),
            ),
        )
        summary = {
            "profile": _profile_payload(profile, focus_ids),
            "team": [
                {
                    "id": member.id,
                    "rufname": member.rufname,
                    "food_display": member.get_food(),
                    "allergies": member.allergien,
                    "money_total": _money(member.dashboard_money_total),
                }
                for member in team
            ],
            "totals": {
                "kids": len(kids),
                "checked_in": sum(kid.anwesend is True for kid in kids),
                "train_arrival": sum(kid.zug_anreise is True for kid in kids),
                "train_departure": sum(kid.zug_abreise is True for kid in kids),
                "pocket_money": _money(money_totals["total"]),
                "pocket_money_paid": _money(money_totals["paid"]),
                "team_money": _money(
                    sum(member.dashboard_money_total for member in team)
                ),
            },
            "kids": [_kid_payload(kid) for kid in kids],
            "focuses": [
                {"id": focus.id, "name": focus.swp_name}
                for focus in focuses
            ],
        }

    return {
        **summary,
        "activity": {
            "notes": _activity_page("notes", turnus_id),
            "transactions": _activity_page("transactions", turnus_id),
        },
    }


CONTRACTS = {
    "dashboard": build_dashboard_contract,
}
