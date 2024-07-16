from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from .views import SchwerpunkteUpdate, MealUpdate, SchwerpunkteDetail, SchwerpunkteCreate, AuslagerorteCreate, AuslagerorteImageUpload, AuslagerorteDetail, AuslagerorteUpdate

urlpatterns = [
    path('update_notiz_abreise/', views.update_notiz_abreise,
         name='update_notiz_abreise'),
    path("upload/", views.uploadFile, name="uploadFile"),
    path('upload_excel/<int:turnus_id>/',
         views.upload_excel, name='upload_excel'),
    path('download-updated-excel/', views.download_updated_excel,
         name='download_updated_excel'),
    #     path('', views.kids_list, name='kids_list'),
    path('all_kids', views.kids_list, name='kids_list'),
    path('zugabreise', views.zugabreise, name='zugabreise'),
    path('zuganreise', views.zuganreise, name='zuganreise'),
    path('kid_details/<int:id>', views.kid_details, name='kid_details'),
    path('check_in/<int:id>', views.check_in, name='check_in'),
    path('check_out/<int:id>', views.check_out, name='check_out'),
    path('serienbrief', views.serienbrief, name='serienbrief'),
    path('murdergame', views.murdergame, name='murdergame'),
    path('schwerpunkt/create',
         SchwerpunkteCreate.as_view(), name='schwerpunkt-create'),
    path('schwerpunkt/<int:pk>/', SchwerpunkteDetail.as_view(),
         name='schwerpunkt-detail'),
    path('schwerpunkt/<int:pk>/update',
         SchwerpunkteUpdate.as_view(), name='schwerpunkt-update'),
    path('swpmeals/<int:pk>', MealUpdate.as_view(), name='swpmeals'),
    path("swp-dashboard/", views.swp_dashboard, name="swp-dashboard"),
    path("auslagerorte-list/", views.auslagerorte_list, name="auslagerorte-list"),
    path('auslagerorte/create',
         AuslagerorteCreate.as_view(), name='auslagerorte-create'),
    path('auslagerorte/<int:pk>/', AuslagerorteDetail.as_view(),
         name='auslagerorte-detail'),
    path('auslagerorte/<int:pk>/update',
         AuslagerorteUpdate.as_view(), name='auslagerorte-update'),
    path('auslagerorte/<int:pk>/upload-image/',
         AuslagerorteImageUpload.as_view(), name='auslagerorte-image-upload'),
    path('toggle_zug_abreise/', views.toggle_zug_abreise,
         name='toggle_zug_abreise'),
    path('kitchen', views.kitchen, name='kitchen'),
    path('swp-einteilung-w1', views.swp_einteilung_w1, name='swp-einteilung-w1'),
    path('swp-einteilung-w2', views.swp_einteilung_w2, name='swp-einteilung-w2'),
    path('update-schwerpunkt-wahl/', views.update_schwerpunkt_wahl,
         name='update_schwerpunkt_wahl'),
    path('update_freunde/', views.update_freunde, name='update_freunde'),
    path('happy-cleaning/', views.happy_cleaning, name='happy_cleaning'),
    path('kindergesamtzahl/', views.kindergesamtzahl, name='kindergesamtzahl'),
    path('budo_familien/', views.budo_families, name='budo_familien'),
    path('upload_spezialfamilien/', views.upload_spezialfamilien,
         name='upload_spezialfamilien'),
    path('spezial_familien/', views.spezial_familien, name='spezial_familien'),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
