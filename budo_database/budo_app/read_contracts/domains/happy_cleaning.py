from django.db.models import Count, Prefetch, Q
from django.http import Http404

from budo_app.happy_cleaning_number_batch import (
    first_happy_cleaning_complete,
    number_batch_projection,
)
from budo_app.happy_cleaning_station_documents import count_tasks, project_tasks
from budo_app.models import (
    HappyCleaning,
    HappyCleaningAssignment,
    HappyCleaningStation,
    Kinder,
    Profil,
    Turnus,
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


def _requested_event(request, *, active_only=True):
    event_id = request.query_params.get("event_id")
    if not event_id or not str(event_id).isdigit():
        raise Http404
    filters = {"id": int(event_id)}
    if active_only:
        filters["turnus_id"] = require_active_turnus_id(request)
    event = (
        HappyCleaning.objects.filter(**filters)
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
    active_turnus_id = require_active_turnus_id(request)
    active_turnus = getattr(request, "active_turnus", None)
    active_start = (
        active_turnus.turnus_beginn
        if active_turnus is not None and active_turnus.id == active_turnus_id
        else Turnus.objects.filter(id=active_turnus_id).values_list(
            "turnus_beginn", flat=True
        ).first()
    )
    if active_start is None:
        raise Http404
    active_year = active_start.year
    requested_year = request.query_params.get("year")
    if requested_year is not None:
        if not str(requested_year).isdigit():
            raise Http404
        loaded_year = int(requested_year)
    else:
        loaded_year = active_year

    events = list(
        HappyCleaning.objects.select_related("turnus").only(
            "id",
            "turnus_id",
            "turnus__turnus_nr",
            "turnus__turnus_beginn",
            "display_number",
            "revision",
            "has_operational_activity",
        )
    )
    years_available = {event.turnus.turnus_beginn.year for event in events}
    if requested_year is not None and loaded_year not in years_available:
        raise Http404
    active_event_ids = {
        event.id for event in events if event.turnus_id == active_turnus_id
    }
    station_fields = (
        "id",
        "happy_cleaning_id",
        "name",
        "max_kids",
        "meeting_point",
        "position",
        "content_document",
        "responsible_profile_id",
    )
    station_rows = (
        HappyCleaningStation.objects.filter(
            happy_cleaning__turnus__turnus_beginn__year=loaded_year,
        )
        .only(*station_fields)
        .annotate(assigned_count=Count("assignments"))
        .order_by("position", "id")
    )
    if loaded_year == active_year:
        station_rows = station_rows.select_related("responsible_profile").only(
            *station_fields,
            "responsible_profile__id",
            "responsible_profile__rufname",
            "responsible_profile__turnus_id",
        )
    stations_by_event = {}
    for station in station_rows:
        responsible = (
            station.responsible_profile
            if station.happy_cleaning_id in active_event_ids else None
        )
        if responsible and responsible.turnus_id != active_turnus_id:
            responsible = None
        stations_by_event.setdefault(station.happy_cleaning_id, []).append({
            "id": station.id,
            "name": station.name,
            "max_kids": station.max_kids,
            "meeting_point": station.meeting_point,
            "responsible": (
                {"id": responsible.id, "name": responsible.rufname}
                if responsible else None
            ),
            "task_item_count": count_tasks(station.content_document)["total"],
            "assigned_count": station.assigned_count,
            "overbooked_count": max(
                station.assigned_count - station.max_kids, 0
            ),
        })

    years = {}
    for event in events:
        year = event.turnus.turnus_beginn.year
        turnuses = years.setdefault(year, {})
        turnus = turnuses.setdefault(event.turnus_id, {
            "id": event.turnus_id,
            "number": event.turnus.turnus_nr,
            "start": event.turnus.turnus_beginn.isoformat(),
            "_start_date": event.turnus.turnus_beginn,
            "is_active": event.turnus_id == active_turnus_id,
            "events": [],
        })
        summary = {
            **_event_summary(event),
            "can_delete": (
                event.turnus_id == active_turnus_id
                and not event.has_operational_activity
            ),
        }
        if year == loaded_year:
            summary["stations"] = stations_by_event.get(event.id, [])
        turnus["events"].append(summary)

    ordered_years = sorted(
        years,
        key=lambda year: (year != active_year, -year),
    )
    if requested_year is not None:
        ordered_years = [loaded_year]
    return {
        "user_id": request.user.id,
        "active_year": active_year,
        "responsible_profiles": (
            [
                {"id": profile.id, "name": profile.rufname}
                for profile in Profil.objects.filter(
                    user__turnus_memberships__turnus_id=active_turnus_id,
                )
                .only("id", "rufname")
                .order_by("rufname", "id")
            ]
            if requested_year is None else []
        ),
        "copy_targets": [
            {
                **_event_summary(event),
                "label": f"Happy Cleaning {event.display_number}",
            }
            for event in events
            if event.turnus_id == active_turnus_id
        ],
        "years": [
            {
                "year": year,
                "is_active": year == active_year,
                "loaded": year == loaded_year,
                "turnuses": [
                    {
                        key: value
                        for key, value in turnus.items()
                        if not key.startswith("_")
                    }
                    for turnus in sorted(
                        years[year].values(),
                        key=lambda turnus: (
                            not turnus["is_active"]
                            if year == active_year else 1,
                            -turnus["_start_date"].toordinal(),
                            -turnus["id"],
                        ),
                    )
                ],
            }
            for year in ordered_years
        ],
    }


def _todo_progress(document):
    counts = count_tasks(document)
    if not counts["total"]:
        return None
    return counts["checked"] * 100 // counts["total"]


def _assignment_for_child(child):
    assignments = child.route_happy_cleaning_assignments
    return assignments[0] if assignments else None


def _assignment_target(assignment):
    if assignment is None:
        return None
    if assignment.is_excused:
        return {
            "id": "excused",
            "name": "Entschuldigt",
            "is_excused": True,
        }
    return {"id": assignment.station_id, "name": assignment.station.name}


def _assignment_child(child):
    assignment = _assignment_for_child(child)
    return {
        "id": child.id,
        "first_name": child.kid_vorname,
        "last_name": child.kid_nachname,
        "full_name": kid_full_name(child.kid_vorname, child.kid_nachname),
        "number": child.happy_cleaning_number,
        "number_version": child.happy_cleaning_number_version,
        "present": child.anwesend,
        "absence_location": child.wo if child.anwesend is False else None,
        "assigned_station": _assignment_target(assignment),
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
        "number": child.happy_cleaning_number,
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
        "overbooked_count": max(assigned_count - station.max_kids, 0),
        "todo_progress_percentage": _todo_progress(station.content_document),
        "children": [
            _station_child(assignment) for assignment in assignments
        ],
    }


def assignment_snapshot(request):
    event = _requested_event(request)
    assignments = (
        HappyCleaningAssignment.objects.filter(
            happy_cleaning_id=event.id,
            child__turnus_id=event.turnus_id,
        ).filter(
            Q(
                target_kind=HappyCleaningAssignment.TargetKind.STATION,
                station__happy_cleaning_id=event.id,
            )
            | Q(
                target_kind=HappyCleaningAssignment.TargetKind.EXCUSED,
                station__isnull=True,
            )
        )
        .select_related("station", "child")
        .only(
            "id",
            "version",
            "target_kind",
            "station_id",
            "station__id",
            "station__name",
            "child_id",
            "child__id",
            "child__kid_vorname",
            "child__kid_nachname",
            "child__happy_cleaning_number",
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
            "happy_cleaning_number_version",
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
            "has_ever_had_assignment",
            "content_document",
        )
        .prefetch_related(
            Prefetch(
                "assignments",
                queryset=assignments,
                to_attr="route_happy_cleaning_assignments",
            ),
        )
    )
    present_total = sum(child.anwesend is True for child in children)
    assigned_present = sum(
        child.anwesend is True and _assignment_for_child(child) is not None
        for child in children
    )
    unlocked = first_happy_cleaning_complete(event.turnus_id, children)
    excused_assignments = [
        assignment
        for child in children
        for assignment in child.route_happy_cleaning_assignments
        if assignment.is_excused
    ]
    return {
        "event": _event_summary(event),
        "summary": {
            "assigned_present": assigned_present,
            "present_total": present_total,
        },
        "number_batch": number_batch_projection(children, unlocked=unlocked),
        "children": [_assignment_child(child) for child in children],
        "stations": [
            *(
                _assignment_station(station, event.turnus_id)
                for station in stations
            ),
            {
                "id": "excused",
                "name": "Entschuldigt",
                "is_excused": True,
                "children": [
                    _station_child(assignment)
                    for assignment in excused_assignments
                ],
            },
        ],
    }


def _requested_station(request, event, *, include_people):
    station_id = request.query_params.get("station_id")
    if not station_id or not str(station_id).isdigit():
        raise Http404
    stations = HappyCleaningStation.objects.filter(
            id=int(station_id),
            happy_cleaning_id=event.id,
        )
    if include_people:
        stations = stations.select_related("responsible_profile")
    station_fields = [
        "id",
        "happy_cleaning_id",
        "name",
        "max_kids",
        "meeting_point",
        "wishes",
        "content_document",
        "version",
    ]
    if include_people:
        station_fields.extend([
            "responsible_profile_id",
            "responsible_profile__id",
            "responsible_profile__rufname",
            "responsible_profile__turnus_id",
        ])
    station = (
        stations
        .only(*station_fields)
        .first()
    )
    if station is None:
        raise Http404
    return station


def _document_projection(document):
    tasks = iter(project_tasks(document))
    blocks = []
    for node in document.get("content", []):
        if node.get("type") == "paragraph":
            blocks.append({
                "type": "paragraph",
                "text": "".join(
                    child["text"] for child in node.get("content", [])
                ),
            })
        elif node.get("type") == "taskList":
            blocks.append({
                "type": "task_list",
                "items": [next(tasks) for _item in node.get("content", [])],
            })
    return blocks


def todo_print(request):
    event = _requested_event(request, active_only=False)
    stations = (
        HappyCleaningStation.objects.filter(happy_cleaning_id=event.id)
        .only("id", "name", "position", "content_document")
        .order_by("position", "id")
    )
    return {
        "event": _event_summary(event),
        "stations": [
            {
                "id": station.id,
                "name": station.name,
                "document": station.content_document,
            }
            for station in stations
        ],
    }


def station_detail(request):
    event = _requested_event(request, active_only=False)
    active = event.turnus_id == require_active_turnus_id(request)
    station = _requested_station(request, event, include_people=active)
    document = _document_projection(station.content_document)
    document_tasks = [
        task
        for block in document
        if block["type"] == "task_list"
        for task in block["items"]
    ]
    todos = [
        {**task, "position": position}
        for position, task in enumerate(document_tasks, start=1)
    ]
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
    ) if active else []
    responsible = station.responsible_profile if active else None
    if responsible and responsible.turnus_id != event.turnus_id:
        responsible = None
    checked_count = sum(todo["checked"] for todo in todos)
    assigned_count = len(assignments)
    copy_targets = HappyCleaning.objects.filter(
        turnus_id=require_active_turnus_id(request),
    )
    if active:
        copy_targets = copy_targets.exclude(id=event.id)
    projection = {
        "event": _event_summary(event),
        "copy_targets": [
            {
                **_event_summary(target),
                "label": f"Happy Cleaning {target.display_number}",
            }
            for target in copy_targets
            .only("id", "display_number", "revision")
            .order_by("display_number", "id")
        ],
        "station": {
            "id": station.id,
            "version": station.version,
            "name": station.name,
            "max_kids": station.max_kids,
            "meeting_point": station.meeting_point,
            "wishes": station.wishes,
            "has_ever_had_assignment": station.has_ever_had_assignment,
            "assigned_count": assigned_count,
            "overbooked_count": max(assigned_count - station.max_kids, 0),
            "content": document,
            "document": station.content_document,
            "is_historical": not active,
            "can_edit": active,
            "can_delete": active and not station.has_ever_had_assignment,
            "can_toggle_tasks": active,
            "todo_checked_count": checked_count,
            "todo_total_count": len(todos),
            "todo_progress_percentage": (
                round(checked_count * 100 / len(todos)) if todos else None
            ),
            "todos": todos,
        },
    }
    if active:
        projection["station"]["responsible"] = (
            {"id": responsible.id, "name": responsible.rufname}
            if responsible else None
        )
        projection["station"]["children"] = [
                {
                    "id": assignment.child_id,
                    "full_name": kid_full_name(
                        assignment.child.kid_vorname,
                        assignment.child.kid_nachname,
                    ),
                    "assignment_version": assignment.version,
                }
                for assignment in assignments
        ]
        projection["responsible_profiles"] = [
            {"id": profile.id, "name": profile.rufname}
            for profile in Profil.objects.filter(
                user__turnus_memberships__turnus_id=event.turnus_id,
            )
            .only("id", "rufname")
            .order_by("rufname", "id")
        ]
    return projection


def _print_name(child):
    return kid_full_name(child.kid_vorname, child.kid_nachname)


def print_number_list(request):
    turnus_id = require_active_turnus_id(request)
    number_batch_event_id = (
        HappyCleaning.objects.filter(turnus_id=turnus_id, display_number=1)
        .values_list("id", flat=True)
        .first()
    )
    children = list(
        Kinder.objects.filter(turnus_id=turnus_id).only(
            "id",
            "kid_vorname",
            "kid_nachname",
            "happy_cleaning_number",
            "happy_cleaning_number_version",
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
    unlocked = first_happy_cleaning_complete(turnus_id, children)
    return {
        "number_batch_event_id": number_batch_event_id,
        "number_batch": number_batch_projection(children, unlocked=unlocked),
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
    "happy-cleaning-todo-print": todo_print,
    "happy-cleaning-overview-station": station_detail,
}
