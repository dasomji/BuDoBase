"""
This is the user views.
"""

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from budo_app.models import Kinder, Profil, TurnusMembership
from budo_app.react_views import ReactPageTemplateMixin, render_react_page
from django.views.decorators.http import require_GET
from django.views.generic.edit import UpdateView
from django.urls import reverse_lazy
from .forms import (
    DUPLICATE_EMAIL_ERROR,
    LoginForm,
    ProfileForm,
    RegisterForm,
    is_email_unique_integrity_error,
)
from budo_app.utils import cache_user_profile
from .dashboard_services import build_dashboard_context


def sign_in(request):

    if request.method == 'GET':
        if request.user.is_authenticated:
            return redirect('/')

        form = LoginForm()
        return render_react_page(request, {'form': form})

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
        form.add_error(None, 'Invalid username or password')
        return render_react_page(request, {'form': form})


def sign_out(request):
    logout(request)
    messages.success(request, f'You have been logged out.')
    return redirect('login')


def sign_up(request):
    if request.user.is_authenticated:
        kids = Kinder.objects.all()
        context = {
            'kids': kids,
        }
        return render_react_page(request, context)

    if request.method == 'GET':
        form = RegisterForm()
        return render_react_page(request, {'form': form})

    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.username.lower()
            try:
                with transaction.atomic():
                    user.save()
            except IntegrityError as error:
                if not is_email_unique_integrity_error(error):
                    raise
                form.add_error("email", DUPLICATE_EMAIL_ERROR)
            else:
                messages.success(request, 'You have signed up successfully.')
                login(request, user)
                return redirect('dashboard')
        return render_react_page(request, {'form': form})


@login_required
@cache_user_profile
def dashboard(request):
    if not request.user_profile:
        messages.error(
            request, "Profile not found. Please contact an administrator.")
        return redirect('login')

    context = build_dashboard_context(request.user_profile, request.active_turnus)

    return render_react_page(request, context)


@login_required
def good_to_know(request):
    return render_react_page(request)


@login_required
@require_GET
def profile_detail(request):
    return render_react_page(request)


class ProfilUpdate(ReactPageTemplateMixin, UpdateView):
    model = Profil
    form_class = ProfileForm
    success_url = reverse_lazy('dashboard')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.request.user.profil

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except IntegrityError as error:
            if not is_email_unique_integrity_error(error):
                raise
            form.add_error("email", DUPLICATE_EMAIL_ERROR)
            return self.form_invalid(form)
        messages.success(self.request, "Profil upgedatet!")
        return response


class ProfilAdminUpdate(ProfilUpdate):
    success_url = reverse_lazy('team-management-page')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        can_edit_shared_turnus_profile = TurnusMembership.objects.filter(
            user=request.user,
            functional_role=TurnusMembership.FunctionalRole.LEITUNG,
            turnus__memberships__user__profil__id=self.kwargs['pk'],
        ).exists()
        if (
            not request.user.has_perm('budo_app.change_profil')
            and not can_edit_shared_turnus_profile
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return get_object_or_404(Profil, pk=self.kwargs['pk'])
