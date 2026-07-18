from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from budo_app.happy_cleaning_commands import (
    CommandError,
    command_context,
    required_positive_integer,
    required_text,
)
from budo_app.happy_cleaning_todo_commands import (
    add_todo,
    check_todo,
    rejection_response,
    reopen_todo,
)


def _error_response(error):
    payload = {"ok": False, "code": error.code}
    if error.errors is not None:
        payload["errors"] = error.errors
    if error.current_version is not None:
        payload["current_version"] = error.current_version
    return Response(payload, status=error.status)


def _run(request, *, action, resource_type, resource_id, operation, created=False):
    context = None
    try:
        context = command_context(request, request.data)
        payload, replayed = operation(context)
    except CommandError as error:
        if context is not None and error.audit_outcome in {"forbidden", "stale"}:
            payload, replayed = rejection_response(
                context,
                action,
                error,
                resource_type=resource_type,
                resource_id=resource_id,
            )
            return Response(payload, status=200 if replayed else error.status)
        return _error_response(error)
    return Response(payload, status=200 if replayed or not created else 201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def todo_add(request, event_id, station_id):
    return _run(
        request,
        action="happy_cleaning.todo.create",
        resource_type="station",
        resource_id=station_id,
        created=True,
        operation=lambda context: add_todo(
            context,
            event_id,
            station_id,
            required_positive_integer(request.data, "expected_version"),
            required_text(request.data, "text", 500),
        ),
    )


def _todo_state_command(request, event_id, station_id, todo_id, *, checked):
    action = (
        "happy_cleaning.todo.check"
        if checked
        else "happy_cleaning.todo.reopen"
    )
    operation = check_todo if checked else reopen_todo
    return _run(
        request,
        action=action,
        resource_type="todo",
        resource_id=todo_id,
        operation=lambda context: operation(
            context,
            event_id,
            station_id,
            todo_id,
            required_positive_integer(request.data, "expected_version"),
        ),
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def todo_check(request, event_id, station_id, todo_id):
    return _todo_state_command(
        request,
        event_id,
        station_id,
        todo_id,
        checked=True,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def todo_reopen(request, event_id, station_id, todo_id):
    return _todo_state_command(
        request,
        event_id,
        station_id,
        todo_id,
        checked=False,
    )
