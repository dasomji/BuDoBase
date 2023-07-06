from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("upload/", views.uploadFile, name="uploadFile"),
    path('', views.budo_app, name='budo_app'),
    path('all_kids', views.kids_list, name='kids_list'),
    path('kid_details/<int:id>', views.kid_details, name='kid_details')
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
