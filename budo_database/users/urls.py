from django.urls import path
from . import views
from .views import ProfilAdminUpdate, ProfilUpdate

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path('login/', views.sign_in, name='login'),
    path('logout/', views.sign_out, name='logout'),
    path('register/', views.sign_up, name='register'),
    path('profil/', ProfilUpdate.as_view(), name='profil'),
    path('profil/<int:pk>/', ProfilAdminUpdate.as_view(), name='profil-admin'),
    path("dashboard/", views.dashboard, name="dashboard"),
]
