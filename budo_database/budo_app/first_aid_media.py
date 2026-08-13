from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404

from .memberships import authorized_turnus_scope
from .models import ErsteHilfeFoto, NotizFoto


@login_required
def attachment_media(request, kind, photo_id):
    # Authorization-sensitive media reads deliberately bypass the five-minute
    # profile cache so a Turnus reassignment revokes access immediately.
    with authorized_turnus_scope(request.user) as active_turnus:
        if active_turnus is None:
            raise Http404
        model = {"notes": NotizFoto, "first-aid": ErsteHilfeFoto}.get(kind)
        if model is None:
            raise Http404
        photo = get_object_or_404(
            model.objects.select_related("eintrag__kinder"), pk=photo_id,
            eintrag__kinder__turnus_id=active_turnus.id,
        )
        try:
            stored_file = photo.datei.open("rb")
        except (FileNotFoundError, OSError, KeyError) as error:
            raise Http404 from error

    response = FileResponse(
        stored_file,
        as_attachment=False,
        filename=f"{kind}-foto-{photo.id}.webp",
        content_type="image/webp",
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
