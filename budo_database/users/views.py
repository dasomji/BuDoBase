"""
This is the user views.
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template import loader

from budo_app.models import Kinder, Profil
from django.views.generic.edit import UpdateView
from django.urls import reverse_lazy
from django.conf import settings
from .forms import LoginForm, RegisterForm
from budo_app.utils import cache_user_profile
from .dashboard_services import build_dashboard_context


def sign_in(request):

    if request.method == 'GET':
        if request.user.is_authenticated:
            return redirect('/')

        form = LoginForm()
        return render(request, 'users/login.html', {'form': form})

    elif request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                messages.success(
                    request, f'Hi {username.title()}, welcome back!')
                return redirect('dashboard')

        # either form not valid or user is not authenticated
        messages.error(request, f'Invalid username or password')
        return render(request, 'users/login.html', {'form': form})


def sign_out(request):
    logout(request)
    messages.success(request, f'You have been logged out.')
    return redirect('login')


def sign_up(request):
    if request.user.is_authenticated:
        template = loader.get_template('users/already_registered.html')
        kids = Kinder.objects.all()
        context = {
            'kids': kids,
        }
        return HttpResponse(template.render(context, request))

    if request.method == 'GET':
        form = RegisterForm()
        return render(request, 'users/register.html', {'form': form})

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        passphrase = request.POST.get('passphrase')

        if form.is_valid() and passphrase == settings.REGISTRATION_PASSPHRASE:
            user = form.save(commit=False)
            user.username = user.username.lower()
            user.save()
            messages.success(request, 'You have signed up successfully.')
            login(request, user)
            return redirect('profil')
        else:
            if passphrase != settings.REGISTRATION_PASSPHRASE:
                messages.error(
                    request, 'Invalid passphrase. Please try again.')
            return render(request, 'users/register.html', {'form': form})


@login_required
@cache_user_profile
def dashboard(request):
    template = loader.get_template('users/dashboard.html')
    if not request.user_profile:
        messages.error(
            request, "Profile not found. Please contact an administrator.")
        return redirect('login')

    context = build_dashboard_context(request.user_profile, request.active_turnus)

    return HttpResponse(template.render(context, request))


class ProfilUpdate(UpdateView):
    model = Profil
    fields = ['rufname', 'allergien', 'coffee', 'rolle',
              'essen', 'telefonnummer', 'turnus']
    template_name = "users/profil.html"
    success_url = reverse_lazy('dashboard')

    def get_form_class(self):
        form_class = super().get_form_class()
        if self.request.user.groups.filter(name='Test-users').exists():
            if 'turnus' in form_class.base_fields:
                form_class.base_fields.pop('turnus')
        return form_class

    def get_object(self, queryset=None):
        return self.request.user.profil

    def form_valid(self, form):
        messages.success(self.request, "Profil upgedatet!")
        return super(ProfilUpdate, self).form_valid(form)
