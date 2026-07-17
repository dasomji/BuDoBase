import logging
import os
from tempfile import TemporaryDirectory

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import loader

from . import models
from .excelProcessor import process_excel
from .forms import UploadForm
from .models import Profil
from .storage_lifecycle import delete_storage_object_on_commit
from .updateExcel import update_excel_file

logger = logging.getLogger(__name__)


@login_required
def uploadFile(request):
    template = loader.get_template('upload-file.html')
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

    return HttpResponse(template.render(context, request))


@login_required
def upload_excel(request, turnus_id):
    turnus = get_object_or_404(models.Turnus, id=turnus_id)
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
    return render(request, 'upload_excel.html', {'form': form, 'turnus': turnus})


@login_required
def download_updated_excel(request):
    profil = Profil.objects.get(user=request.user)
    active_turnus = profil.turnus

    if not active_turnus:
        return HttpResponse("No active turnus found.", status=404)

    filename = (
        f"Aufenthaltsdoku_{active_turnus}_ID{active_turnus.id}.xlsx"
    )
    temporary_directory = TemporaryDirectory()
    file_path = os.path.join(temporary_directory.name, filename)

    try:
        update_excel_file(file_path, active_turnus)
        response = FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename=filename,
        )
    except Exception:
        temporary_directory.cleanup()
        raise

    close_response = response.close

    def close_and_clean_up():
        try:
            close_response()
        finally:
            temporary_directory.cleanup()

    response.close = close_and_clean_up
    return response
