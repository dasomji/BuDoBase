from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("upload/", views.uploadFile, name="uploadFile"),
    path('', views.kids_list, name='budo_app'),
    path('all_kids', views.kids_list, name='kids_list'),
    path('kid_details/<int:id>', views.kid_details, name='kid_details'),
    path('test', views.testing, name='testing'),
    path('budo_families/', views.budo_family_overview,
         name='budo_family_overview'),
    path('budo_familie/<str:budo_family>',
         views.budo_family, name='budo_family'),
    path('postprocess', views.postprocess, name='postprocess'),
    path('check_in/<int:id>', views.check_in, name='check_in'),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
