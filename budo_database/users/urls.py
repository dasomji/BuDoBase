from django.urls import path
from . import views
from .views import ProfilUpdate

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path('login/', views.sign_in, name='login'),
    path('logout/', views.sign_out, name='logout'),
    path('register/', views.sign_up, name='register'),
    path('profil/', ProfilUpdate.as_view(), name='profil'),
    path("dashboard/", views.dashboard, name="dashboard"),
]
