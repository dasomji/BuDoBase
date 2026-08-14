from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from .views import SchwerpunkteUpdate, MealUpdate, SchwerpunkteDetail, SchwerpunkteCreate, AuslagerorteCreate, AuslagerorteImageUpload, AuslagerorteDetail, AuslagerorteUpdate
from .tag_views import create_tag, delete_tag, tag_settings_page, update_tag
from .place_views import delete_place, delete_place_image
from .settings_views import admin_settings_page, recalculate_travel_times
from .first_aid_media import attachment_media
from .happy_cleaning_page_views import (
    assignment_page,
    event_print_number_page,
    print_number_page,
)
from .kid_edit_views import kid_edit_page
from .join_request_views import request_turnus_membership
from .join_request_decision_views import decide_turnus_join_request
from .admin_team_views import create_leitung_membership, create_turnus, set_membership_leadership
from .excel_views import upload_turnus_excel
from .team_membership_views import create_teamer_membership, remove_team_membership, update_team_membership_label


def legacy_slashless_page(route, view, *, name):
    """Register a canonical page URL plus its legacy slashless form.

    New page routes should use a trailing slash. This compatibility helper is
    only for routes that were historically published without one, especially
    POST targets that cannot rely on APPEND_SLASH without losing request data.
    """
    canonical_route = route.rstrip('/') + '/'
    legacy_route = route.rstrip('/')
    return (
        path(canonical_route, view),
        path(legacy_route, view, name=name),
    )


urlpatterns = [
    path('api/turnusse/', create_turnus, name='turnus-create-api'),
    path(
        'api/turnusse/<int:turnus_id>/excel/',
        upload_turnus_excel,
        name='turnus-excel-upload-api',
    ),
    path(
        'api/join-requests/<int:join_request_id>/decision/',
        decide_turnus_join_request,
        name='join-request-decision-api',
    ),
    path(
        'api/turnusse/<int:turnus_id>/join-requests/',
        request_turnus_membership,
        name='turnus-join-request-api',
    ),
    path('api/admin/memberships/<int:membership_id>/role/', set_membership_leadership, name='admin-membership-role-api'),
    path('api/admin/turnusse/<int:turnus_id>/leitung/', create_leitung_membership, name='admin-leitung-membership-create-api'),
    path('api/turnusse/<int:turnus_id>/memberships/', create_teamer_membership, name='teamer-membership-create-api'),
    path('api/memberships/<int:membership_id>/label/', update_team_membership_label, name='membership-label-api'),
    path('api/memberships/<int:membership_id>/remove/', remove_team_membership, name='membership-remove-api'),
    path('settings/', admin_settings_page, name='admin-settings-page'),
    path(
        'api/settings/recalculate-travel-times/',
        recalculate_travel_times,
        name='recalculate-travel-times-api',
    ),
    path('api/places/<int:place_id>/delete/', delete_place, name='place-delete-api'),
    path(
        'api/places/<int:place_id>/images/<int:image_id>/delete/',
        delete_place_image,
        name='place-image-delete-api',
    ),
    path('api/place-tags/', create_tag, name='place-tag-create-api'),
    path('api/place-tags/<int:tag_id>/update/', update_tag, name='place-tag-update-api'),
    path('api/place-tags/<int:tag_id>/delete/', delete_tag, name='place-tag-delete-api'),
    path('auslagerorte/tags/', tag_settings_page, name='place-tag-settings'),
    path(
        'api/attachments/<str:kind>/<int:photo_id>/',
        attachment_media,
        name='attachment-media',
    ),
    path('update_notiz_abreise/', views.update_notiz_abreise,
         name='update_notiz_abreise'),
    path("upload/", views.uploadFile, name="uploadFile"),
    path('upload_excel/<int:turnus_id>/',
         views.upload_excel, name='upload_excel'),
    path('download-updated-excel/', views.download_updated_excel,
         name='download_updated_excel'),
    #     path('', views.kids_list, name='kids_list'),
    *legacy_slashless_page('all_kids', views.kids_list, name='kids_list'),
    *legacy_slashless_page('zugabreise', views.zugabreise, name='zugabreise'),
    *legacy_slashless_page('zuganreise', views.zuganreise, name='zuganreise'),
    *legacy_slashless_page(
        'kid_details/<int:id>', views.kid_details, name='kid_details'
    ),
    *legacy_slashless_page(
        'kid_details/<int:kid_id>/edit', kid_edit_page, name='kid-edit-page'
    ),
    *legacy_slashless_page('check_in/<int:id>', views.check_in, name='check_in'),
    *legacy_slashless_page(
        'check_out/<int:id>', views.check_out, name='check_out'
    ),
    *legacy_slashless_page('serienbrief', views.serienbrief, name='serienbrief'),
    *legacy_slashless_page('murdergame', views.murdergame, name='murdergame'),
    *legacy_slashless_page(
        'schwerpunkt/create',
        SchwerpunkteCreate.as_view(),
        name='schwerpunkt-create',
    ),
    path('schwerpunkt/<int:pk>/', SchwerpunkteDetail.as_view(),
         name='schwerpunkt-detail'),
    *legacy_slashless_page(
        'schwerpunkt/<int:pk>/update',
        SchwerpunkteUpdate.as_view(),
        name='schwerpunkt-update',
    ),
    *legacy_slashless_page(
        'swpmeals/<int:pk>', MealUpdate.as_view(), name='swpmeals'
    ),
    path("swp-dashboard/", views.swp_dashboard, name="swp-dashboard"),
    path("auslagerorte-list/", views.auslagerorte_list, name="auslagerorte-list"),
    *legacy_slashless_page(
        'auslagerorte/create',
        AuslagerorteCreate.as_view(),
        name='auslagerorte-create',
    ),
    path('auslagerorte/<int:pk>/', AuslagerorteDetail.as_view(),
         name='auslagerorte-detail'),
    *legacy_slashless_page(
        'auslagerorte/<int:pk>/update',
        AuslagerorteUpdate.as_view(),
        name='auslagerorte-update',
    ),
    path('auslagerorte/<int:pk>/upload-image/',
         AuslagerorteImageUpload.as_view(), name='auslagerorte-image-upload'),
    path('toggle_zug_abreise/', views.toggle_zug_abreise,
         name='toggle_zug_abreise'),
    *legacy_slashless_page('kitchen', views.kitchen, name='kitchen'),
    *legacy_slashless_page(
        'swp-einteilung-w1', views.swp_einteilung_w1, name='swp-einteilung-w1'
    ),
    *legacy_slashless_page(
        'swp-einteilung-w2', views.swp_einteilung_w2, name='swp-einteilung-w2'
    ),
    path('update-schwerpunkt-wahl/', views.update_schwerpunkt_wahl,
         name='update_schwerpunkt_wahl'),
    path('update_freunde/', views.update_freunde, name='update_freunde'),
    path('update_pfand/', views.update_pfand, name='update_pfand'),
    path(
        'happy-cleaning/<int:event_id>/assignment/',
        assignment_page,
        name='happy-cleaning-assignment-page',
    ),
    path(
        'happy-cleaning/print/',
        print_number_page,
        name='happy-cleaning-print-page',
    ),
    path(
        'happy-cleaning/<int:event_id>/print/',
        event_print_number_page,
        name='happy-cleaning-event-print-page',
    ),
    path('happy-cleaning/', views.happy_cleaning, name='happy_cleaning'),
    path('kindergesamtzahl/', views.kindergesamtzahl, name='kindergesamtzahl'),
    path('budo_familien/', views.budo_families, name='budo_familien'),
    path('upload_spezialfamilien/', views.upload_spezialfamilien,
         name='upload_spezialfamilien'),
    path('spezial_familien/', views.spezial_familien, name='spezial_familien'),
    path('kindergeburtstage/', views.kindergeburtstage, name='kindergeburtstage'),
    path('update-birthdays-from-sv/', views.update_birthdays_from_sv,
         name='update_birthdays_from_sv'),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
