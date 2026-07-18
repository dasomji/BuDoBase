from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from budo_app.happy_cleaning_assignment_commands import (
    AssignmentCommandError,
    NUMBER_COMMAND_ACTION,
    assign_child,
    move_child,
    rejection_response,
    remove_child,
    set_child_number,
)
from budo_app.happy_cleaning_commands import (
    CommandError,
    command_context,
    required_positive_integer,
)


def _error_response(error):
    payload = {"ok": False, "code": error.code}
    if error.errors is not None:
        payload["errors"] = error.errors
    if error.current_version is not None:
        payload["current_version"] = error.current_version
    if isinstance(error, AssignmentCommandError):
        payload.update(error.projection)
    return Response(payload, status=error.status)


def _number(payload):
    value = payload.get("number")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CommandError(
            "validation_error",
            errors={"number": ["A positive integer or null is required."]},
        )
    return value


def _run(request, action, operation):
    if request.content_type != "application/json":
        return Response(
            {"ok": False, "code": "unsupported_media_type"},
            status=415,
        )
    context = None
    try:
        context = command_context(request, request.data)
        payload, replayed = operation(context)
    except AssignmentCommandError as error:
        if context is None:
            return _error_response(error)
        payload, replayed = rejection_response(context, action, error)
        return Response(payload, status=200 if replayed else error.status)
    except CommandError as error:
        return _error_response(error)
    return Response(payload, status=200 if replayed else 200)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def child_number(request, child_id):
    return _run(
        request,
        NUMBER_COMMAND_ACTION,
        lambda context: set_child_number(
            context,
            child_id,
            _number(request.data),
            required_positive_integer(request.data, "expected_version"),
        ),
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def assignment_assign(request, event_id):
    action = "happy_cleaning.assignment.assign"
    return _run(
        request,
        action,
        lambda context: assign_child(
            context,
            event_id,
            required_positive_integer(request.data, "child_id"),
            required_positive_integer(request.data, "station_id"),
        ),
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def assignment_move(request, event_id, child_id):
    action = "happy_cleaning.assignment.move"
    return _run(
        request,
        action,
        lambda context: move_child(
            context,
            event_id,
            child_id,
            required_positive_integer(request.data, "station_id"),
            required_positive_integer(request.data, "expected_version"),
        ),
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def assignment_remove(request, event_id, child_id):
    action = "happy_cleaning.assignment.remove"
    return _run(
        request,
        action,
        lambda context: remove_child(
            context,
            event_id,
            child_id,
            required_positive_integer(request.data, "expected_version"),
        ),
    )
