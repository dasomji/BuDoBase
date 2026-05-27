from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from .models import Kinder, SpezialFamilien, Profil, BetreuerinnenGeld
from .forms import CSVUploadForm, BetreuerinnenGeldForm, BirthdayNotizForm
from django.views.decorators.http import require_POST
from django.db import transaction
from .utils import cache_user_profile, get_active_kid_or_404, get_turnus_data_optimized, parse_json_body, safe_get_object_or_404
import csv
import pandas as pd
import logging
from .auslagerorte_views import (
    AuslagerorteCreate,
    AuslagerorteDetail,
    AuslagerorteImageUpload,
    AuslagerorteUpdate,
    auslagerorte_list,
)
from .excel_views import download_updated_excel, upload_excel, uploadFile
from .kids_views import (
    budo_families,
    check_in,
    check_out,
    kid_details,
    kids_list,
    murdergame,
    serienbrief,
    spezial_familien,
    toggle_zug_abreise,
    update_notiz_abreise,
    zugabreise,
    zuganreise,
)
from .schwerpunkte_views import (
    MealUpdate,
    SchwerpunkteCreate,
    SchwerpunkteDetail,
    SchwerpunkteUpdate,
    kitchen,
    swp_dashboard,
    swp_einteilung,
    swp_einteilung_w1,
    swp_einteilung_w2,
    update_freunde,
    update_schwerpunkt_wahl,
)

logger = logging.getLogger(__name__)


@login_required
@cache_user_profile
@csrf_protect
@require_POST
def update_pfand(request):
    """
    AJAX endpoint to update pfand value for a kid.
    Accepts 'increase' or 'decrease' action.
    """
    data = parse_json_body(request)
    if data is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    kid_id = data.get('id')
    action = data.get('action')  # 'increase' or 'decrease'
    kid = get_active_kid_or_404(request, kid_id)

    try:
        if action == 'increase':
            kid.pfand += 1
        elif action == 'decrease':
            # Ensure pfand doesn't go below 0
            if kid.pfand > 0:
                kid.pfand -= 1
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid action'})

        kid.save()

        return JsonResponse({
            'status': 'success',
            'new_pfand': kid.pfand,
            'remaining_taschengeld': kid.get_remaining_taschengeld()
        })
    except Kinder.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Kid not found'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
def happy_cleaning(request):
    # Get the current turnus (you might need to adjust this based on how you store the current turnus)
    current_turnus = request.user.profil.turnus

    # Query kids from the current turnus
    kids = Kinder.objects.filter(turnus=current_turnus)

    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="happy_cleaning.csv"'

    # Create the CSV writer
    writer = csv.writer(response)
    writer.writerow(['ID', 'Kindername'])

    # Write data rows
    for kid in kids:
        writer.writerow([kid.id, f"{kid.kid_vorname} {kid.kid_nachname}"])

    return response


@login_required
def kindergesamtzahl(request):
    current_user = request.user
    profil = Profil.objects.get(user=current_user)
    active_turnus = profil.turnus
    checked_in_count = Kinder.objects.filter(
        turnus=active_turnus, anwesend=True).count()
    total_kids = Kinder.objects.filter(turnus=active_turnus).count()
    context = {
        'checked_in_count': checked_in_count,
        'total_kids': total_kids,
    }
    return render(request, 'kindergesamtzahl.html', context)


@login_required
def upload_spezialfamilien(request):
    if request.method == "POST":
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            xlsx_file = request.FILES['csv_file']
            current_user = request.user
            profil = Profil.objects.get(user=current_user)
            active_turnus = profil.turnus

            try:
                with transaction.atomic():
                    df = pd.read_excel(xlsx_file)

                    # Normalize column names to lower case and strip spaces
                    df.columns = df.columns.str.strip().str.lower()

                    # Check for the 'index' and 'coven' columns
                    if 'index' not in df.columns or 'coven' not in df.columns:
                        raise ValueError(
                            "XLSX file must contain 'Index' and 'Coven' columns")

                    # Strip whitespace from all string columns
                    for column in df.select_dtypes(include=['object']).columns:
                        df[column] = df[column].str.strip()

                    updated_count = 0
                    for _, row in df.iterrows():
                        kid_index = str(row['index']).strip()
                        coven_name = str(row['coven']).strip()

                        # Skip rows with no index or summary rows
                        if pd.isna(kid_index) or kid_index == '' or 'Kiddos' in kid_index:
                            continue

                        try:
                            # Assuming kid_index in the database is stored as "T2-39"
                            kid = Kinder.objects.get(
                                kid_index=kid_index, turnus=active_turnus)

                            spezial_familie, created = SpezialFamilien.objects.get_or_create(
                                name=coven_name,
                                turnus=active_turnus
                            )

                            kid.spezial_familien = spezial_familie
                            kid.save()
                            updated_count += 1

                        except Kinder.DoesNotExist:
                            logger.warning(
                                f"Kid with index {kid_index} not found, skipping")
                            continue

                    messages.success(
                        request, f"Spezialfamilien wurden erfolgreich aktualisiert. {updated_count} Kinder wurden zugeordnet.")
                    logger.info(
                        f"Successfully updated {updated_count} kids with spezialfamilien")
                    return redirect('upload_spezialfamilien')
            except Exception as e:
                logger.error(
                    f"Error processing spezialfamilien file: {str(e)}")
                messages.error(
                    request, f"Ein Fehler ist aufgetreten: {str(e)}")
    else:
        form = CSVUploadForm()

    return render(request, 'uploadspezialfamilien.html', {'form': form})


@login_required
def teamer_details(request, id):
    current_user = request.user
    profil = Profil.objects.get(user=current_user)
    active_turnus = profil.turnus
    this_profil = get_object_or_404(Profil, id=id, turnus=active_turnus)
    geld = BetreuerinnenGeld.objects.filter(who=this_profil)

    context = {
        "profil": this_profil,
        "geld": geld,
    }

    if request.method == 'POST':
        geld_form = BetreuerinnenGeldForm(request.POST)
        context["geld_form"] = geld_form

        if geld_form.is_valid():
            amount = geld_form.cleaned_data.get("amount")
            what = geld_form.cleaned_data.get("what")
            if amount and what:
                geld = geld_form.save(commit=False)
                geld.what = what
                geld.amount = amount
                geld.who = this_profil
                geld.save()
            return redirect('teamer_details', id=this_profil.id)
        else:
            logger.debug("BetreuerinnenGeld form is not valid: %s",
                         geld_form.errors)
    else:
        geld_form = BetreuerinnenGeldForm()
        context["geld_form"] = geld_form

    return render(request, 'users/teamer.html', context)


@login_required
@cache_user_profile
def kindergeburtstage(request):
    if not request.user_profile:
        messages.error(
            request, "Profile not found. Please contact an administrator.")
        return redirect('dashboard')

    turnus_data = get_turnus_data_optimized(request.active_turnus)
    kids = turnus_data['kids']

    # Process birthday data for each kid
    kids_with_birthday_data = []
    for kid in kids:
        birthday_data = {
            'kid': kid,
            'database_birthday': kid.kid_birthday,
            'sv_birthday': None,
            'birthdays_match': False
        }

        # Calculate birthday from sozialversicherungsnr if available
        if kid.sozialversicherungsnr:
            try:
                # Remove spaces and any non-digit characters for sanitization
                cleaned_sv = ''.join(
                    filter(str.isdigit, kid.sozialversicherungsnr))

                # Austrian SV format: XXXX DDMMYY (first 4 digits + 6 digit birthday)
                if len(cleaned_sv) >= 10:
                    # Get last 6 digits: DDMMYY
                    birthday_part = cleaned_sv[-6:]
                    day = int(birthday_part[:2])
                    month = int(birthday_part[2:4])
                    year_short = int(birthday_part[4:6])

                    # Determine full year (assuming 2000s if under 50, 1900s if 50+)
                    if year_short < 50:
                        year = 2000 + year_short
                    else:
                        year = 1900 + year_short

                    from datetime import date
                    sv_birthday = date(year, month, day)
                    birthday_data['sv_birthday'] = sv_birthday

                    # Check if birthdays match
                    if kid.kid_birthday and sv_birthday == kid.kid_birthday:
                        birthday_data['birthdays_match'] = True

            except (ValueError, TypeError, IndexError):
                # Invalid date in sozialversicherungsnr
                pass

        kids_with_birthday_data.append(birthday_data)

    # Handle note submission
    if request.method == 'POST':
        kid_id = request.POST.get('kid_id')
        birthday_notiz_form = BirthdayNotizForm(request.POST)

        if kid_id and birthday_notiz_form.is_valid():
            notiz = birthday_notiz_form.cleaned_data.get('notiz')
            if notiz:
                kid = safe_get_object_or_404(
                    Kinder, id=kid_id, turnus=request.active_turnus)
                new_notiz = birthday_notiz_form.save(commit=False)
                new_notiz.kinder = kid
                new_notiz.added_by = request.user
                new_notiz.save()
                return redirect('kindergeburtstage')

    birthday_notiz_form = BirthdayNotizForm()

    context = {
        'kids_with_birthday_data': kids_with_birthday_data,
        'birthday_notiz_form': birthday_notiz_form,
        'schwerpunkte': turnus_data['schwerpunkte'],
        'auslagerorte': turnus_data['auslagerorte'],
    }

    return render(request, 'kindergeburtstage.html', context)


@login_required
@cache_user_profile
@require_POST
@csrf_protect
def update_birthdays_from_sv(request):
    """Update all kids' birthdays based on their sozialversicherungsnr"""
    if not request.user_profile:
        messages.error(
            request, "Profile not found. Please contact an administrator.")
        return redirect('dashboard')

    turnus_data = get_turnus_data_optimized(request.active_turnus)
    kids = turnus_data['kids']

    updated_count = 0
    error_count = 0
    errors = []

    try:
        with transaction.atomic():
            for kid in kids:
                if kid.sozialversicherungsnr:
                    try:
                        # Remove spaces and any non-digit characters for sanitization
                        cleaned_sv = ''.join(
                            filter(str.isdigit, kid.sozialversicherungsnr))

                        # Austrian SV format: XXXX DDMMYY (first 4 digits + 6 digit birthday)
                        if len(cleaned_sv) >= 10:
                            # Get last 6 digits: DDMMYY
                            birthday_part = cleaned_sv[-6:]
                            day = int(birthday_part[:2])
                            month = int(birthday_part[2:4])
                            year_short = int(birthday_part[4:6])

                            # Determine full year (assuming 2000s if under 50, 1900s if 50+)
                            if year_short < 50:
                                year = 2000 + year_short
                            else:
                                year = 1900 + year_short

                            from datetime import date
                            sv_birthday = date(year, month, day)

                            # Only update if the birthday is different or missing
                            if kid.kid_birthday != sv_birthday:
                                old_birthday = kid.kid_birthday
                                kid.kid_birthday = sv_birthday
                                kid.save()
                                updated_count += 1

                                # Log the change
                                logger.info(f"Updated birthday for {kid.kid_vorname} {kid.kid_nachname} "
                                            f"from {old_birthday} to {sv_birthday}")

                    except (ValueError, TypeError, IndexError) as e:
                        error_count += 1
                        error_msg = f"Error processing {kid.kid_vorname} {kid.kid_nachname}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)

            # Success message
            if updated_count > 0:
                messages.success(
                    request, f"Successfully updated {updated_count} birthdays from SV numbers.")
            else:
                messages.info(request, "No birthdays needed updating.")

            if error_count > 0:
                messages.warning(
                    request, f"{error_count} errors occurred during update. Check logs for details.")

    except Exception as e:
        logger.error(f"Transaction failed during birthday update: {str(e)}")
        messages.error(request, f"Update failed: {str(e)}")

    return redirect('kindergeburtstage')
