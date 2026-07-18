from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from budo_app.happy_cleaning_commands import (
    CommandError,
    audit_rejection,
    command_context,
    copy_stations,
    create_station,
    create_todo,
    create_event,
    delete_station,
    delete_todo,
    delete_event,
    reorder_stations,
    reorder_todos,
    required_id_list,
    required_positive_integer,
    required_text,
    station_fields,
    update_station,
    update_todo,
)


def _error_response(error):
    payload = {"ok": False, "code": error.code}
    if error.errors is not None:
        payload["errors"] = error.errors
    if error.current_version is not None:
        payload["current_version"] = error.current_version
    payload.update(error.extra)
    return Response(payload, status=error.status)


def _run_command(
    request,
    *,
    action,
    resource_type,
    resource_id,
    resource_label,
    operation,
    created=False,
):
    context = None
    try:
        context = command_context(request, request.data)
        payload, replayed = operation(context)
    except CommandError as error:
        if context is not None:
            audit_rejection(
                context,
                error,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_label=resource_label,
            )
        return _error_response(error)
    return Response(payload, status=200 if replayed or not created else 201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def event_create(request):
    try:
        context = command_context(request, request.data)
        payload, replayed = create_event(context)
    except CommandError as error:
        return _error_response(error)
    return Response(payload, status=200 if replayed else 201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def event_delete(request, event_id):
    context = None
    try:
        context = command_context(request, request.data)
        expected_revision = required_positive_integer(
            request.data,
            "expected_revision",
        )
        payload, replayed = delete_event(
            context,
            event_id,
            expected_revision,
        )
    except CommandError as error:
        if context is not None:
            audit_rejection(
                context,
                error,
                action="happy_cleaning.event.delete",
                resource_type="happy_cleaning",
                resource_id=event_id,
                resource_label=f"Happy Cleaning #{event_id}",
            )
        return _error_response(error)
    return Response(payload, status=200)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def station_create(request, event_id):
    return _run_command(
        request,
        action="happy_cleaning.station.create",
        resource_type="happy_cleaning",
        resource_id=event_id,
        resource_label=f"Happy Cleaning #{event_id}",
        created=True,
        operation=lambda context: create_station(
            context,
            event_id,
            required_positive_integer(request.data, "expected_revision"),
            station_fields(request.data),
        ),
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def station_update(request, event_id, station_id):
    return _run_command(
        request,
        action="happy_cleaning.station.update",
        resource_type="station",
        resource_id=station_id,
        resource_label=f"Station #{station_id}",
        operation=lambda context: update_station(
            context,
            event_id,
            station_id,
            required_positive_integer(request.data, "expected_version"),
            station_fields(request.data),
        ),
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def station_delete(request, event_id, station_id):
    return _run_command(
        request,
        action="happy_cleaning.station.delete",
        resource_type="station",
        resource_id=station_id,
        resource_label=f"Station #{station_id}",
        operation=lambda context: delete_station(
            context,
            event_id,
            station_id,
            required_positive_integer(request.data, "expected_version"),
        ),
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def station_reorder(request, event_id):
    return _run_command(
        request,
        action="happy_cleaning.station.reorder",
        resource_type="happy_cleaning",
        resource_id=event_id,
        resource_label=f"Happy Cleaning #{event_id}",
        operation=lambda context: reorder_stations(
            context,
            event_id,
            required_positive_integer(request.data, "expected_revision"),
            required_id_list(request.data, "station_ids"),
        ),
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def todo_create(request, event_id, station_id):
    return _run_command(
        request,
        action="happy_cleaning.todo.create",
        resource_type="station",
        resource_id=station_id,
        resource_label=f"Station #{station_id}",
        created=True,
        operation=lambda context: create_todo(
            context,
            event_id,
            station_id,
            required_positive_integer(request.data, "expected_version"),
            required_text(request.data, "text", 500),
        ),
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def todo_update(request, event_id, station_id, todo_id):
    return _run_command(
        request,
        action="happy_cleaning.todo.update",
        resource_type="todo",
        resource_id=todo_id,
        resource_label=f"Todo #{todo_id}",
        operation=lambda context: update_todo(
            context,
            event_id,
            station_id,
            todo_id,
            required_positive_integer(request.data, "expected_version"),
            required_text(request.data, "text", 500),
        ),
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def todo_delete(request, event_id, station_id, todo_id):
    return _run_command(
        request,
        action="happy_cleaning.todo.delete",
        resource_type="todo",
        resource_id=todo_id,
        resource_label=f"Todo #{todo_id}",
        operation=lambda context: delete_todo(
            context,
            event_id,
            station_id,
            todo_id,
            required_positive_integer(request.data, "expected_version"),
        ),
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def todo_reorder(request, event_id, station_id):
    return _run_command(
        request,
        action="happy_cleaning.todo.reorder",
        resource_type="station",
        resource_id=station_id,
        resource_label=f"Station #{station_id}",
        operation=lambda context: reorder_todos(
            context,
            event_id,
            station_id,
            required_positive_integer(request.data, "expected_version"),
            required_id_list(request.data, "todo_ids"),
        ),
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def station_copy(request, event_id):
    def operation(context):
        copy_all = request.data.get("copy_all") is True
        station_ids = request.data.get("station_ids")
        if not copy_all:
            station_ids = required_id_list(request.data, "station_ids")
        return copy_stations(
            context,
            event_id,
            required_positive_integer(request.data, "expected_revision"),
            required_positive_integer(request.data, "source_event_id"),
            copy_all=copy_all,
            station_ids=station_ids,
            duplicate_strategy=request.data.get("duplicate_strategy"),
        )

    return _run_command(
        request,
        action="happy_cleaning.station.copy",
        resource_type="happy_cleaning",
        resource_id=event_id,
        resource_label=f"Happy Cleaning #{event_id}",
        operation=operation,
    )
