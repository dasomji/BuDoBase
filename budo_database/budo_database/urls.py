"""
URL configuration for budo_database project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from budo_app.api_views import submit_form
from budo_app.read_contracts.bootstrap import bootstrap
from budo_app.read_contracts.views import route_data

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/bootstrap/', bootstrap, name='bootstrap-api'),
    path(
        'api/route-data/<slug:contract_key>/',
        route_data,
        name='route-data-api',
    ),
    path('api/form-submit/', submit_form, name='form-submit-api'),
    path('', include('budo_app.urls')),
    path('', include('users.urls'))
]
