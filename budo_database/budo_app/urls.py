from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from .views import SchwerpunkteUpdate, MealUpdate, SchwerpunkteDetail, SchwerpunkteCreate, AuslagerorteCreate, AuslagerorteDetail, AuslagerorteUpdate

urlpatterns = [
    path('update_notiz_abreise/', views.update_notiz_abreise,
         name='update_notiz_abreise'),
    path("upload/", views.uploadFile, name="uploadFile"),
    #     path('', views.kids_list, name='kids_list'),
    path('all_kids', views.kids_list, name='kids_list'),
    path('zuganreise', views.zuganreise, name='zuganreise'),
    path('kid_details/<int:id>', views.kid_details, name='kid_details'),
    path('postprocess', views.postprocess, name='postprocess'),
    path('check_in/<int:id>', views.check_in, name='check_in'),
    path('check_out/<int:id>', views.check_out, name='check_out'),
    path('serienbrief', views.serienbrief, name='serienbrief'),
    path('murdergame', views.murdergame, name='murdergame'),
    path('schwerpunkt/create',
         SchwerpunkteCreate.as_view(), name='schwerpunkt-create'),
    path('schwerpunkt/<int:pk>', SchwerpunkteDetail.as_view(),
         name='schwerpunkt-detail'),
    path('schwerpunkt/<int:pk>/update',
         SchwerpunkteUpdate.as_view(), name='schwerpunkt-update'),
    path('swpmeals/<int:pk>', MealUpdate.as_view(), name='swpmeals'),
    path("swp-dashboard/", views.swp_dashboard, name="swp-dashboard"),
    path("auslagerorte-list/", views.auslagerorte_list, name="auslagerorte-list"),
    path('auslagerorte/create',
         AuslagerorteCreate.as_view(), name='auslagerorte-create'),
    path('auslagerorte/<int:pk>', AuslagerorteDetail.as_view(),
         name='auslagerorte-detail'),
    path('auslagerorte/<int:pk>/update',
         AuslagerorteUpdate.as_view(), name='auslagerorte-update'),
    path('toggle_zug_abreise/', views.toggle_zug_abreise,
         name='toggle_zug_abreise'),
    # path('check_in_list/<int:id>', views.check_in_list, name='check_in_all'),
    # path('test', views.testing, name='testing'),
    # path('budo_families/', views.budo_family_overview,
    #      name='budo_family_overview'),
    # path('budo_familie/<str:budo_family>',
    #      views.budo_family, name='budo_family'),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
