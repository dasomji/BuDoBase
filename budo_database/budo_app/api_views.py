from html import unescape
import re

from django.contrib import messages
from django.urls import resolve
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

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
        r'<(?:ul|li|small)[^>]*class="[^"]*(?:errorlist|error)[^"]*"[^>]*>(.*?)</(?:ul|li|small)>',
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
