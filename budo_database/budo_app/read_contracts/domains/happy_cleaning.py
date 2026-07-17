from django.db.models import Prefetch
from django.http import Http404

from budo_app.models import (
    HappyCleaning,
    HappyCleaningAssignment,
    HappyCleaningStation,
    HappyCleaningTodo,
    Kinder,
    Profil,
)
from budo_app.read_contracts.common import (
    kid_full_name,
    require_active_turnus_id,
)


def _event_summary(event):
    return {
        "id": event.id,
        "display_number": event.display_number,
        "revision": event.revision,
    }


def _requested_event(request):
    event_id = request.query_params.get("event_id")
    if not event_id or not str(event_id).isdigit():
        raise Http404
    event = (
        HappyCleaning.objects.filter(
            id=int(event_id),
            turnus_id=require_active_turnus_id(request),
        )
        .only(
            "id",
            "turnus_id",
            "display_number",
            "revision",
            "has_operational_activity",
        )
        .first()
    )
    if event is None:
        raise Http404
    return event


def overview(request):
    events = HappyCleaning.objects.filter(
        turnus_id=require_active_turnus_id(request),
    ).only(
        "id",
        "display_number",
        "revision",
        "has_operational_activity",
    )
    return {
        "events": [
            {
                **_event_summary(event),
                "can_delete": not event.has_operational_activity,
            }
            for event in events
        ],
    }


def _todo_progress(todos):
    if not todos:
        return None
    checked = sum(todo.checked for todo in todos)
    return checked * 100 // len(todos)


def _assignment_for_child(child):
    assignments = child.route_happy_cleaning_assignments
    return assignments[0] if assignments else None


def _assignment_child(child):
    assignment = _assignment_for_child(child)
    return {
        "id": child.id,
        "first_name": child.kid_vorname,
        "last_name": child.kid_nachname,
        "full_name": kid_full_name(child.kid_vorname, child.kid_nachname),
        "number": child.happy_cleaning_number,
        "present": child.anwesend,
        "absence_location": child.wo if child.anwesend is False else None,
        "assigned_station": (
            {"id": assignment.station_id, "name": assignment.station.name}
            if assignment else None
        ),
        "assignment_version": assignment.version if assignment else None,
    }


def _station_child(assignment):
    child = assignment.child
    return {
        "id": child.id,
        "full_name": kid_full_name(child.kid_vorname, child.kid_nachname),
        "short_name": (
            f"{child.kid_vorname} {child.kid_nachname[:2]}".strip()
        ),
        "present": child.anwesend,
        "assignment_version": assignment.version,
    }


def _assignment_station(station, turnus_id):
    assignments = station.route_happy_cleaning_assignments
    responsible = station.responsible_profile
    if responsible and responsible.turnus_id != turnus_id:
        responsible = None
    assigned_count = len(assignments)
    return {
        "id": station.id,
        "version": station.version,
        "name": station.name,
        "wishes": station.wishes,
        "meeting_point": station.meeting_point,
        "responsible": (
            {"id": responsible.id, "name": responsible.rufname}
            if responsible else None
        ),
        "max_kids": station.max_kids,
        "assigned_count": assigned_count,
        "free_seats": max(station.max_kids - assigned_count, 0),
        "todo_progress_percentage": _todo_progress(station.route_todos),
        "children": [
            _station_child(assignment) for assignment in assignments
        ],
    }


def assignment_snapshot(request):
    event = _requested_event(request)
    assignments = (
        HappyCleaningAssignment.objects.filter(
            happy_cleaning_id=event.id,
            station__happy_cleaning_id=event.id,
            child__turnus_id=event.turnus_id,
        )
        .select_related("station", "child")
        .only(
            "id",
            "version",
            "station_id",
            "station__id",
            "station__name",
            "child_id",
            "child__id",
            "child__kid_vorname",
            "child__kid_nachname",
            "child__anwesend",
        )
        .order_by("child__kid_vorname", "child__kid_nachname", "child_id")
    )
    children = list(
        Kinder.objects.filter(turnus_id=event.turnus_id)
        .only(
            "id",
            "kid_vorname",
            "kid_nachname",
            "happy_cleaning_number",
            "anwesend",
            "wo",
        )
        .prefetch_related(Prefetch(
            "happy_cleaning_assignments",
            queryset=assignments,
            to_attr="route_happy_cleaning_assignments",
        ))
        .order_by("kid_vorname", "kid_nachname", "id")
    )
    todos = HappyCleaningTodo.objects.only(
        "id",
        "station_id",
        "checked",
    ).order_by("position", "id")
    stations = list(
        HappyCleaningStation.objects.filter(happy_cleaning_id=event.id)
        .select_related("responsible_profile")
        .only(
            "id",
            "happy_cleaning_id",
            "name",
            "max_kids",
            "meeting_point",
            "wishes",
            "responsible_profile_id",
            "responsible_profile__id",
            "responsible_profile__rufname",
            "responsible_profile__turnus_id",
            "position",
            "version",
        )
        .prefetch_related(
            Prefetch(
                "assignments",
                queryset=assignments,
                to_attr="route_happy_cleaning_assignments",
            ),
            Prefetch("todos", queryset=todos, to_attr="route_todos"),
        )
    )
    present_total = sum(child.anwesend is True for child in children)
    assigned_present = sum(
        child.anwesend is True and _assignment_for_child(child) is not None
        for child in children
    )
    return {
        "event": _event_summary(event),
        "summary": {
            "assigned_present": assigned_present,
            "present_total": present_total,
        },
        "children": [_assignment_child(child) for child in children],
        "stations": [
            _assignment_station(station, event.turnus_id)
            for station in stations
        ],
    }


def _todo(todo):
    return {
        "id": todo.id,
        "text": todo.text,
        "position": todo.position,
        "checked": todo.checked,
        "version": todo.version,
    }


def _management_station(station, turnus_id):
    responsible_profile_id = (
        station.responsible_profile_id
        if station.responsible_profile
        and station.responsible_profile.turnus_id == turnus_id
        else None
    )
    return {
        "id": station.id,
        "version": station.version,
        "name": station.name,
        "max_kids": station.max_kids,
        "meeting_point": station.meeting_point,
        "wishes": station.wishes,
        "responsible_profile_id": responsible_profile_id,
        "position": station.position,
        "has_ever_had_assignment": station.has_ever_had_assignment,
        "todo_progress_percentage": _todo_progress(station.route_todos),
        "todos": [_todo(todo) for todo in station.route_todos],
    }


def station_management(request):
    event = _requested_event(request)
    todos = HappyCleaningTodo.objects.only(
        "id",
        "station_id",
        "text",
        "position",
        "checked",
        "version",
    ).order_by("position", "id")
    stations = (
        HappyCleaningStation.objects.filter(happy_cleaning_id=event.id)
        .select_related("responsible_profile")
        .only(
            "id",
            "happy_cleaning_id",
            "name",
            "max_kids",
            "meeting_point",
            "wishes",
            "responsible_profile_id",
            "responsible_profile__id",
            "responsible_profile__turnus_id",
            "position",
            "version",
            "has_ever_had_assignment",
        )
        .prefetch_related(Prefetch(
            "todos",
            queryset=todos,
            to_attr="route_todos",
        ))
    )
    profiles = Profil.objects.filter(turnus_id=event.turnus_id).only(
        "id",
        "rufname",
    ).order_by("rufname", "id")
    return {
        "event": _event_summary(event),
        "responsible_profiles": [
            {"id": profile.id, "name": profile.rufname}
            for profile in profiles
        ],
        "stations": [
            _management_station(station, event.turnus_id)
            for station in stations
        ],
    }


def _requested_station(request, event):
    station_id = request.query_params.get("station_id")
    if not station_id or not str(station_id).isdigit():
        raise Http404
    station = (
        HappyCleaningStation.objects.filter(
            id=int(station_id),
            happy_cleaning_id=event.id,
        )
        .select_related("responsible_profile")
        .only(
            "id",
            "happy_cleaning_id",
            "name",
            "meeting_point",
            "wishes",
            "responsible_profile_id",
            "responsible_profile__id",
            "responsible_profile__rufname",
            "responsible_profile__turnus_id",
            "version",
        )
        .first()
    )
    if station is None:
        raise Http404
    return station


def station_detail(request):
    event = _requested_event(request)
    station = _requested_station(request, event)
    todos = list(
        HappyCleaningTodo.objects.filter(station_id=station.id)
        .only("id", "station_id", "text", "position", "checked", "version")
        .order_by("position", "id")
    )
    assignments = list(
        HappyCleaningAssignment.objects.filter(
            happy_cleaning_id=event.id,
            station_id=station.id,
            child__turnus_id=event.turnus_id,
        )
        .select_related("child")
        .only(
            "id",
            "version",
            "child_id",
            "child__id",
            "child__kid_vorname",
            "child__kid_nachname",
        )
        .order_by("child__kid_vorname", "child__kid_nachname", "child_id")
    )
    responsible = station.responsible_profile
    if responsible and responsible.turnus_id != event.turnus_id:
        responsible = None
    return {
        "event": _event_summary(event),
        "station": {
            "id": station.id,
            "version": station.version,
            "name": station.name,
            "meeting_point": station.meeting_point,
            "wishes": station.wishes,
            "responsible": (
                {"id": responsible.id, "name": responsible.rufname}
                if responsible else None
            ),
            "todo_progress_percentage": _todo_progress(todos),
            "children": [
                {
                    "id": assignment.child_id,
                    "full_name": kid_full_name(
                        assignment.child.kid_vorname,
                        assignment.child.kid_nachname,
                    ),
                    "assignment_version": assignment.version,
                }
                for assignment in assignments
            ],
            "todos": [_todo(todo) for todo in todos],
        },
    }


def _print_name(child):
    return kid_full_name(child.kid_vorname, child.kid_nachname)


def print_number_list(request):
    event = _requested_event(request)
    children = list(
        Kinder.objects.filter(turnus_id=event.turnus_id).only(
            "id",
            "kid_vorname",
            "kid_nachname",
            "happy_cleaning_number",
            "anwesend",
            "wo",
        )
    )
    present_numbered = sorted(
        (
            child for child in children
            if child.anwesend is True
            and child.happy_cleaning_number is not None
        ),
        key=lambda child: (
            child.happy_cleaning_number,
            _print_name(child).casefold(),
            child.id,
        ),
    )
    present_numberless = sorted(
        (
            child for child in children
            if child.anwesend is True
            and child.happy_cleaning_number is None
        ),
        key=lambda child: (_print_name(child).casefold(), child.id),
    )
    absent = sorted(
        (child for child in children if child.anwesend is not True),
        key=lambda child: (_print_name(child).casefold(), child.id),
    )
    return {
        "event": _event_summary(event),
        "present_numbered": [
            {
                "id": child.id,
                "full_name": _print_name(child),
                "number": child.happy_cleaning_number,
            }
            for child in present_numbered
        ],
        "present_numberless": [
            {"id": child.id, "full_name": _print_name(child)}
            for child in present_numberless
        ],
        "absent": [
            {
                "id": child.id,
                "full_name": _print_name(child),
                "number": child.happy_cleaning_number,
                "absence_location": child.wo,
            }
            for child in absent
        ],
    }


CONTRACTS = {
    "happy-cleaning-assignment": assignment_snapshot,
    "happy-cleaning-overview": overview,
    "happy-cleaning-print": print_number_list,
    "happy-cleaning-station-detail": station_detail,
    "happy-cleaning-stations": station_management,
}
