import logging
import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import loader

from . import models
from .excelProcessor import process_excel
from .forms import UploadForm
from .models import Profil
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
            form.save()
            try:
                process_excel(turnus)
                messages.success(
                    request, "Excel-Datei wurde erfolgreich verarbeitet.")
                logger.info(
                    f"Excel file processed successfully for turnus {turnus.id}")
                return redirect('uploadFile')
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
        form = UploadForm(instance=turnus)
    return render(request, 'upload_excel.html', {'form': form, 'turnus': turnus})


@login_required
def download_updated_excel(request):
    profil = Profil.objects.get(user=request.user)
    active_turnus = profil.turnus

    if not active_turnus:
        return HttpResponse("No active turnus found.", status=404)

    file_path = os.path.join(
        settings.MEDIA_ROOT, f"Aufenthaltsdoku_{active_turnus}_ID{active_turnus.id}.xlsx")

    update_excel_file(file_path, active_turnus)

    response = FileResponse(
        open(file_path, 'rb'), as_attachment=True, filename=os.path.basename(file_path))
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'

    def delete_file():
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning("Error deleting generated Excel file: %s", e)

    response.close = delete_file

    return response
