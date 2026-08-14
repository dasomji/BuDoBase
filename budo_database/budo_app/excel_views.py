import logging
import os
import shutil
from tempfile import TemporaryDirectory

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect

from . import models
from .excelProcessor import process_excel
from .forms import UploadForm
from .export_snapshots import (
    close_snapshot_with_response,
    create_export_snapshot,
    stream_snapshot,
)
from .memberships import authorized_turnus_scope
from .models import TurnusMembership
from .product_admin_policy import require_product_admin
from .react_views import render_react_page
from .storage_lifecycle import delete_storage_object_on_commit
from .updateExcel import update_excel_file

logger = logging.getLogger(__name__)


@login_required
def uploadFile(request):
    require_product_admin(request.user, "Turnus import access denied.")
    documents = models.Turnus.objects.all()
    context = {
        "documents": documents,
    }
    if request.method == "POST":
        upload_form = UploadForm(request.POST, request.FILES)
        context["upload_form"] = upload_form
        if upload_form.is_valid():
            turnus = upload_form.save()
            if 'uploadedFile' in request.FILES:
                try:
                    process_excel(turnus)
                    messages.success(
                        request, "Excel-Datei wurde erfolgreich verarbeitet.")
                    logger.info(
                        f"Excel file processed successfully for turnus {turnus.id}")
                except Exception as e:
                    logger.error(
                        f"Excel processing failed for turnus {turnus.id}: {str(e)}")
                    messages.error(
                        request, f"Fehler beim Verarbeiten der Excel-Datei: {str(e)}")
                    if turnus.uploadedFile:
                        turnus.uploadedFile.delete()
                        turnus.uploadedFile = None
                        turnus.save()

    else:
        upload_form = UploadForm()
        context["upload_form"] = upload_form

    return render_react_page(request, context)


@login_required
def upload_excel(request, turnus_id):
    turnuses = models.Turnus.objects.all()
    if not request.user.is_superuser:
        turnuses = turnuses.filter(
            memberships__user_id=request.user.pk,
            memberships__functional_role=TurnusMembership.FunctionalRole.LEITUNG,
        )
    turnus = get_object_or_404(turnuses, id=turnus_id)
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES, instance=turnus)
        if form.is_valid():
            persisted_turnus = models.Turnus.objects.only(
                "uploadedFile"
            ).get(pk=turnus.pk)
            previous_file = persisted_turnus.uploadedFile
            previous_name = previous_file.name
            previous_storage = previous_file.storage
            turnus._defer_replaced_file_cleanup = True

            try:
                with transaction.atomic():
                    turnus = form.save()
                    process_excel(turnus)
                    current_name = turnus.uploadedFile.name
                    if previous_name and previous_name != current_name:
                        delete_storage_object_on_commit(
                            previous_storage,
                            previous_name,
                        )
                messages.success(
                    request, "Excel-Datei wurde erfolgreich verarbeitet.")
                logger.info(
                    f"Excel file processed successfully for turnus {turnus.id}")
                return redirect('uploadFile')
            except Exception as e:
                failed_file = turnus.uploadedFile
                if (
                    failed_file.name
                    and failed_file.name != previous_name
                    and failed_file._committed
                ):
                    delete_storage_object_on_commit(
                        failed_file.storage,
                        failed_file.name,
                    )
                logger.error(
                    f"Excel processing failed for turnus {turnus.id}: {str(e)}")
                messages.error(
                    request, f"Fehler beim Verarbeiten der Excel-Datei: {str(e)}")
            finally:
                if hasattr(turnus, "_defer_replaced_file_cleanup"):
                    del turnus._defer_replaced_file_cleanup
                if hasattr(turnus, "_replaced_storage_file"):
                    del turnus._replaced_storage_file
    else:
        form = UploadForm(instance=turnus)
    return render_react_page(request, {'form': form, 'turnus': turnus})


@login_required
def download_updated_excel(request):
    snapshot = None
    with authorized_turnus_scope(request.user) as active_turnus:
        if not active_turnus:
            return HttpResponse("No active turnus found.", status=404)
        filename = f"Aufenthaltsdoku_{active_turnus}_ID{active_turnus.id}.xlsx"
        temporary_directory = TemporaryDirectory()
        file_path = os.path.join(temporary_directory.name, filename)
        try:
            update_excel_file(file_path, active_turnus)
            snapshot = create_export_snapshot()
            with open(file_path, "rb") as generated_file:
                shutil.copyfileobj(generated_file, snapshot)
            snapshot.seek(0)
        except Exception:
            if snapshot is not None:
                snapshot.close()
            temporary_directory.cleanup()
            raise

    temporary_directory.cleanup()
    response = FileResponse(snapshot, as_attachment=True, filename=filename)
    # FileResponse registers the snapshot for response-close cleanup. Stream it
    # through the shared generator as well so normal exhaustion closes it.
    response.streaming_content = stream_snapshot(snapshot)
    return close_snapshot_with_response(response, snapshot)
