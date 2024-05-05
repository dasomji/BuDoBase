from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.http import HttpResponse
from django.template import loader
from .forms import LoginForm, RegisterForm
from budo_app.forms import ProfilForm
from budo_app.models import Kinder, Profil
from django.views.generic.edit import CreateView, UpdateView
from django.urls import reverse_lazy
from django.db.models import Q


def sign_in(request):

    if request.method == 'GET':
        if request.user.is_authenticated:
            return redirect('kids_list')

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
                return redirect('kids_list')

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
        print(kids)
        # return render(request, 'users/already_registered.html', {"context": context})
        return HttpResponse(template.render(context, request))

    if request.method == 'GET':
        form = RegisterForm()
        return render(request, 'users/register.html', {'form': form})

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.username.lower()
            user.save()
            messages.success(request, 'You have singed up successfully.')
            login(request, user)
            return redirect('profil')
        else:
            return render(request, 'users/register.html', {'form': form})


def dashboard(request):
    template = loader.get_template('users/dashboard.html')
    current_user = request.user
    profil = Profil.objects.get(user=current_user)
    kids = Kinder.objects.all()
    anzahl_kids = Kinder.objects.all().count()
    kids_zug_anreise_count = Kinder.objects.filter(zug_anreise=True).count()
    kids_zug_abreise_count = Kinder.objects.filter(zug_abreise=True).count()
    male_kids_count = Kinder.objects.filter(sex="männlich").count()
    female_kids_count = Kinder.objects.filter(sex="weiblich").count()
    diverse_kids_count = Kinder.objects.exclude(
        sex__in=["männlich", "weiblich"]).count()
    kids_mit_budo_erfahrung = Kinder.objects.filter(
        budo_erfahrung=True).count()
    # geburtstagskinder = [
    #     kid for kid in kids if kid.is_birthday_during_turnus()]
    geburtstagskinder = sorted(
        [kid for kid in kids if kid.is_birthday_during_turnus()],
        key=lambda kid: (kid.kid_birthday.month, kid.kid_birthday.day)
    )
    geburtstage = len(geburtstagskinder)
    eingecheckte_kids = Kinder.objects.filter(anwesend=True).count()
    team = Profil.objects.all()

    medikamente = [kid for kid in kids if kid.get_clean_drugs()]
    gesundheit = [kid for kid in kids if kid.get_clean_illness()]
    kids_attention = [kid for kid in kids if (
        kid.get_clean_drugs() or kid.get_clean_illness())]
    ersties = Kinder.objects.filter(budo_erfahrung=False)
    ersties_count = ersties.count()
    context = {
        "profil": profil,
        "kids": kids,
        "kids_zug_anreise_count": kids_zug_anreise_count,
        "kids_zug_abreise_count": kids_zug_abreise_count,
        "male_kids_count": male_kids_count,
        "female_kids_count": female_kids_count,
        "diverse_kids_count": diverse_kids_count,
        "kids_mit_budo_erfahrung": kids_mit_budo_erfahrung,
        "geburtstagskinder": geburtstagskinder,
        "geburtstage": geburtstage,
        "eingecheckte_kids": eingecheckte_kids,
        "anzahl_kids": anzahl_kids,
        "team": team,
        "medikamente": medikamente,
        "gesundheit": gesundheit,
        "kids_attention": kids_attention,
        "ersties": ersties,
        "ersties_count": ersties_count,
    }

    return HttpResponse(template.render(context, request))


class ProfilUpdate(UpdateView):
    model = Profil
    fields = ['rufname', 'allergien', 'rolle',
              'essen', 'telefonnummer', 'turnus']
    template_name = "users/profil.html"
    success_url = reverse_lazy('dashboard')

    def get_object(self, queryset=None):
        return self.request.user.profil

    def form_valid(self, form):
        messages.success(self.request, "Profil upgedatet!")
        return super(ProfilUpdate, self).form_valid(form)
