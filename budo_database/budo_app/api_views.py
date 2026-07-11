from collections import defaultdict
from html import unescape
import re

from django.contrib import messages
from django.db.models import Prefetch, Sum
from django.middleware.csrf import get_token
from django.urls import resolve
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import (
    Auslagerorte,
    BetreuerinnenGeld,
    Geld,
    Kinder,
    Notizen,
    Profil,
    Schwerpunkte,
    SchwerpunktWahl,
    Schwerpunktzeit,
    Turnus,
)


FORM_TARGETS = (
    r"/login/?", r"/register/?", r"/profil/?", r"/upload/?",
    r"/upload_excel/\d+/?", r"/kid_details/\d+/?", r"/check_in/\d+/?",
    r"/check_out/\d+/?", r"/schwerpunkt/create/?",
    r"/schwerpunkt/\d+/update/?", r"/swpmeals/\d+/?",
    r"/auslagerorte/create/?", r"/auslagerorte/\d+/update/?",
    r"/auslagerorte/\d+/upload-image/?", r"/auslagerorte/\d+/?",
    r"/upload_spezialfamilien/?", r"/kindergeburtstage/?", r"/teamer/\d+/?",
    r"/update-birthdays-from-sv/?",
)


def _response_errors(html):
    blocks = re.findall(
        r'<(?:ul|li)[^>]*class="[^"]*(?:errorlist|error)[^"]*"[^>]*>(.*?)</(?:ul|li)>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return [
        unescape(re.sub(r"<[^>]+>", " ", block)).strip()
        for block in blocks
        if re.sub(r"<[^>]+>", "", block).strip()
    ]


@api_view(["POST"])
@permission_classes([AllowAny])
def submit_form(request):
    """REST adapter for the established Django form/domain handlers.

    React owns form rendering and state. The existing handlers remain the
    single source of validation and business rules while this adapter turns
    redirects and bound-form errors into a stable JSON contract.
    """
    target = request.data.get("_target", "")
    if not any(re.fullmatch(pattern, target) for pattern in FORM_TARGETS):
        return Response({"ok": False, "errors": ["Ungültiges Formularziel."]}, status=400)

    raw_request = request._request
    original_path = raw_request.path
    original_path_info = raw_request.path_info
    try:
        match = resolve(target)
        raw_request.path = target
        raw_request.path_info = target
        response = match.func(raw_request, *match.args, **match.kwargs)
        if hasattr(response, "render") and not response.is_rendered:
            response.render()
    finally:
        raw_request.path = original_path
        raw_request.path_info = original_path_info

    if 300 <= response.status_code < 400:
        return Response({"ok": True, "redirect": response.get("Location", target)})

    if response.status_code >= 400:
        return Response(
            {"ok": False, "errors": [f"Formular konnte nicht gespeichert werden ({response.status_code})."]},
            status=response.status_code,
        )

    html = response.content.decode(response.charset)
    errors = _response_errors(html)
    message_storage = messages.get_messages(raw_request)
    handler_messages = list(message_storage)
    message_storage.used = False
    errors.extend(
        str(message)
        for message in handler_messages
        if "error" in message.tags
    )
    if errors:
        return Response({"ok": False, "errors": errors}, status=422)
    return Response({"ok": True, "redirect": target})


def _date(value):
    return value.isoformat() if value else None


def _datetime(value):
    return value.isoformat() if value else None


def _money(value):
    return round(float(value or 0), 2)


def _note(note):
    return {
        "id": note.id,
        "text": note.notiz or "",
        "date": _datetime(note.date_added),
        "day": note.date_added.strftime("%d.%m.") if note.date_added else "",
        "author": note.added_by.username,
    }


def _transaction(transaction):
    return {
        "id": transaction.id,
        "amount": _money(transaction.amount),
        "date": _datetime(transaction.date_added),
        "day": transaction.date_added.strftime("%d.%m.") if transaction.date_added else "",
        "author": transaction.added_by.username,
    }


def _kid(kid):
    focus_by_week = {
        focus.schwerpunktzeit.woche: focus
        for focus in kid.schwerpunkte.all()
        if focus.schwerpunktzeit
    }
    choices = []
    for choice in kid.schwerpunkt_wahl.all():
        choices.append(
            {
                "week": choice.schwerpunktzeit.woche,
                "first": choice.erste_wahl_id,
                "second": choice.zweite_wahl_id,
                "third": choice.dritte_wahl_id,
                "friends": choice.freunde,
            }
        )

    return {
        "id": kid.id,
        "index": kid.kid_index,
        "first_name": kid.kid_vorname,
        "last_name": kid.kid_nachname,
        "full_name": f"{kid.kid_vorname} {kid.kid_nachname}".strip(),
        "birthday": _date(kid.kid_birthday),
        "birthday_during_turnus": kid.is_birthday_during_turnus(),
        "age": kid.get_alter(),
        "sex": kid.sex,
        "sex_short": kid.get_short_sex(),
        "weeks": kid.turnus_dauer,
        "siblings": kid.get_clean_geschwister(),
        "tent_request": kid.get_clean_zeltwunsch(),
        "budo_experience": kid.budo_erfahrung,
        "present": kid.anwesend,
        "where": kid.wo,
        "check_in_date": _date(kid.check_in_date),
        "late_arrival": _date(kid.late_anreise),
        "early_departure": _date(kid.early_abreise_date),
        "came_back": _date(kid.came_back),
        "id_card": kid.ausweis,
        "e_card": kid.e_card,
        "consent": kid.einverstaendnis_erklaerung,
        "train_arrival": kid.zug_anreise,
        "train_departure": kid.zug_abreise,
        "departure_note": kid.notiz_abreise,
        "youth_ticket": kid.top_jugendticket,
        "budo_family": kid.budo_family,
        "special_family": str(kid.spezial_familien) if kid.spezial_familien else None,
        "focus_w1": str(focus_by_week.get("w1", "---")),
        "focus_w2": str(focus_by_week.get("w2", "---")),
        "focus_ids": [focus.id for focus in kid.schwerpunkte.all()],
        "choices": choices,
        "food": kid.get_food(),
        "vegetarian": kid.vegetarisch,
        "special_food": kid.get_clean_special_food(),
        "drugs": kid.get_clean_drugs(),
        "illness": kid.get_clean_illness(),
        "swimmer": kid.swimmer,
        "social_security_number": kid.sozialversicherungsnr,
        "tetanus": kid.tetanusimpfung,
        "tick_vaccine": kid.zeckenimpfung,
        "over_the_counter_medication": kid.rezeptfreie_medikamente,
        "prescription_medication": kid.rezept_medikamente,
        "booking_note": kid.get_clean_anmerkung_buchung(),
        "note": kid.get_clean_anmerkung(),
        "team_note": kid.anmerkung_team,
        "organization": kid.anmelde_organisation,
        "registrant_name": f"{kid.anmelder_vorname} {kid.anmelder_nachname}".strip(),
        "registrant_email": kid.anmelder_email,
        "registrant_phone": kid.anmelder_mobil,
        "insured_with": kid.hauptversichert_bei,
        "emergency_contacts": kid.notfall_kontakte,
        "deposit": kid.pfand,
        "pocket_money": _money(kid.get_taschengeld_sum()),
        "remaining_money": _money(kid.get_remaining_taschengeld()),
        "notes": [_note(note) for note in kid.notizen.all()],
        "transactions": [_transaction(item) for item in kid.geld.all()],
    }


def _profile(profile):
    return {
        "id": profile.id,
        "username": profile.user.username,
        "email": profile.user.email,
        "rufname": profile.rufname,
        "phone": str(profile.telefonnummer),
        "allergies": profile.allergien,
        "coffee": profile.coffee,
        "role": profile.rolle,
        "role_display": profile.get_rolle(),
        "food": profile.essen,
        "food_display": profile.get_food(),
        "focus_ids": list(profile.swp.values_list("id", flat=True)),
        "money_total": _money(profile.get_geld_sum()),
        "money_items": [
            {
                "id": item.id,
                "amount": _money(item.amount),
                "what": item.what,
                "date": _datetime(item.date_added),
                "day": item.date_added.strftime("%d.%m.") if item.date_added else "",
            }
            for item in profile.betreuerinnen_geld.all()
        ],
    }


def _focus(focus):
    time = focus.schwerpunktzeit
    meals = defaultdict(dict)
    meal_items = []
    for meal in focus.meals.all():
        meals[str(meal.day)][meal.meal_type] = meal.meal_choice
        meal_items.append(
            {
                "id": meal.id,
                "day": meal.day,
                "type": meal.meal_type,
                "choice": meal.meal_choice,
            }
        )
    return {
        "id": focus.id,
        "name": focus.swp_name,
        "description": focus.beschreibung,
        "place_id": focus.ort_id,
        "place": str(focus.ort) if focus.ort else None,
        "coordinates": focus.ort.koordinaten if focus.ort else None,
        "carer_ids": list(focus.betreuende.values_list("id", flat=True)),
        "carers": focus.get_betreuende_names(),
        "week": time.woche if time else "u",
        "time_id": time.id if time else None,
        "time": str(time) if time else None,
        "start": _date(time.swp_beginn) if time else None,
        "duration": time.dauer if time else 0,
        "off_site": focus.auslagern,
        "departure": _datetime(focus.geplante_abreise),
        "arrival": _datetime(focus.geplante_ankunft),
        "kid_ids": list(focus.swp_kinder.values_list("id", flat=True)),
        "meals": meals,
        "meal_items": meal_items,
    }


def _place(place):
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
        "images": [image.image.url for image in place.images.all() if image.image],
        "notes": [
            {
                "id": note.id,
                "text": note.notiz or "",
                "author": note.added_by.username,
                "date": _datetime(note.date_added),
                "day": note.date_added.strftime("%d.%m.") if note.date_added else "",
            }
            for note in place.auslagernotizen.all()
        ],
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def app_data(request):
    """Return the normalized data graph used by all React routes."""
    csrf_token = get_token(request)
    queued_messages = [
        {"text": str(message), "tags": message.tags}
        for message in messages.get_messages(request._request)
    ]
    if not request.user.is_authenticated:
        return Response(
            {
                "authenticated": False,
                "csrf_token": csrf_token,
                "messages": queued_messages,
            }
        )

    try:
        profile = Profil.objects.select_related("user", "turnus").get(
            user=request.user
        )
    except Profil.DoesNotExist:
        return Response(
            {
                "authenticated": True,
                "user": {"username": request.user.username},
                "profile": None,
                "csrf_token": csrf_token,
                "messages": queued_messages,
            }
        )

    turnus = profile.turnus
    kid_queryset = (
        Kinder.objects.filter(turnus=turnus)
        .select_related("turnus", "spezial_familien")
        .prefetch_related(
            "schwerpunkte__schwerpunktzeit",
            "notizen__added_by",
            "geld__added_by",
            Prefetch(
                "schwerpunkt_wahl",
                queryset=SchwerpunktWahl.objects.select_related(
                    "schwerpunktzeit", "erste_wahl", "zweite_wahl", "dritte_wahl"
                ),
            ),
        )
        .order_by("kid_vorname", "kid_nachname")
    )
    focus_queryset = (
        Schwerpunkte.objects.filter(schwerpunktzeit__turnus=turnus)
        .select_related("ort", "schwerpunktzeit")
        .prefetch_related("betreuende", "meals", "swp_kinder")
        .order_by("schwerpunktzeit__woche", "swp_name")
    )
    places = Auslagerorte.objects.prefetch_related(
        "images", "auslagernotizen__added_by"
    ).order_by("name")
    team = (
        Profil.objects.filter(turnus=turnus)
        .select_related("user")
        .prefetch_related("swp", "betreuerinnen_geld")
        .order_by("rufname")
    )
    kids = list(kid_queryset)

    return Response(
        {
            "authenticated": True,
            "csrf_token": csrf_token,
            "messages": queued_messages,
            "permissions": {
                "change_kids": request.user.has_perm("budo_app.change_kinder"),
                "change_focuses": request.user.has_perm("budo_app.change_schwerpunkte"),
                "change_places": request.user.has_perm("budo_app.change_auslagerorte"),
            },
            "profile": _profile(profile),
            "turnus": (
                {
                    "id": turnus.id,
                    "label": str(turnus),
                    "number": turnus.turnus_nr,
                    "start": _date(turnus.turnus_beginn),
                    "end": _date(turnus.get_turnus_ende()),
                }
                if turnus
                else None
            ),
            "turnuses": [
                {
                    "id": item.id,
                    "label": str(item),
                    "number": item.turnus_nr,
                    "start": _date(item.turnus_beginn),
                }
                for item in Turnus.objects.order_by("-turnus_beginn")
            ],
            "focus_times": [
                {
                    "id": item.id,
                    "label": str(item),
                    "week": item.woche,
                    "duration": item.dauer,
                    "start": _date(item.swp_beginn),
                }
                for item in Schwerpunktzeit.objects.filter(turnus=turnus).order_by("woche")
            ],
            "kids": [_kid(kid) for kid in kids],
            "team": [_profile(item) for item in team],
            "focuses": [_focus(item) for item in focus_queryset],
            "places": [_place(item) for item in places],
            "totals": {
                "kids": len(kids),
                "checked_in": sum(kid.anwesend is True for kid in kids),
                "train_arrival": sum(kid.zug_anreise is True for kid in kids),
                "train_departure": sum(kid.zug_abreise is True for kid in kids),
                "pocket_money": _money(
                    Geld.objects.filter(kinder__turnus=turnus).aggregate(total=Sum("amount"))["total"]
                ),
                "pocket_money_paid": _money(
                    Geld.objects.filter(kinder__turnus=turnus, amount__gt=0).aggregate(total=Sum("amount"))["total"]
                ),
                "team_money": _money(
                    BetreuerinnenGeld.objects.filter(who__turnus=turnus).aggregate(total=Sum("amount"))["total"]
                ),
            },
            "activity": {
                "notes": [
                    {**_note(note), "kid_id": note.kinder_id, "kid": str(note.kinder)}
                    for note in Notizen.objects.filter(kinder__turnus=turnus)
                    .select_related("kinder", "added_by")
                    .order_by("-date_added")
                ],
                "transactions": [
                    {
                        **_transaction(item),
                        "kid_id": item.kinder_id,
                        "kid": str(item.kinder),
                    }
                    for item in Geld.objects.filter(kinder__turnus=turnus)
                    .select_related("kinder", "added_by")
                    .order_by("-date_added")
                ],
            },
        }
    )
