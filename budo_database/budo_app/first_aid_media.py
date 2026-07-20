from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404

from .models import ErsteHilfeFoto, NotizFoto, Profil


@login_required
def attachment_media(request, kind, photo_id):
    # Authorization-sensitive media reads deliberately bypass the five-minute
    # profile cache so a Turnus reassignment revokes access immediately.
    active_turnus_id = (
        Profil.objects.filter(user_id=request.user.id)
        .values_list("turnus_id", flat=True)
        .first()
    )
    if active_turnus_id is None:
        raise Http404

    model = {"notes": NotizFoto, "first-aid": ErsteHilfeFoto}.get(kind)
    if model is None:
        raise Http404
    photo = get_object_or_404(
        model.objects.select_related("eintrag__kinder"),
        pk=photo_id,
        eintrag__kinder__turnus_id=active_turnus_id,
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
