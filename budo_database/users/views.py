from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.http import HttpResponse
from django.template import loader
from .forms import LoginForm, RegisterForm
from budo_app.forms import ProfilForm
from budo_app.models import Kinder, Profil, Notizen, Geld, BetreuerinnenGeld
from django.views.generic.edit import CreateView, UpdateView
from django.urls import reverse_lazy
from django.db.models import Sum
from django.conf import settings


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


def dashboard(request):
    template = loader.get_template('users/dashboard.html')
    current_user = request.user
    if not current_user.is_authenticated:
        # Redirect to the login page if not authenticated
        return redirect('login')
    profil = Profil.objects.get(user=current_user)
    active_turnus = profil.turnus

    kids = Kinder.objects.filter(turnus=active_turnus)
    anzahl_kids = kids.count()
    kids_zug_anreise_count = kids.filter(zug_anreise=True).count()
    kids_zug_abreise_count = kids.filter(zug_abreise=True).count()
    male_kids_count = kids.filter(sex="männlich").count()
    female_kids_count = kids.filter(sex="weiblich").count()
    diverse_kids_count = kids.exclude(
        sex__in=["männlich", "weiblich"]).count()
    kids_mit_budo_erfahrung = kids.filter(
        budo_erfahrung=True).count()
    geburtstagskinder = sorted(
        [kid for kid in kids if kid.is_birthday_during_turnus()],
        key=lambda kid: (kid.kid_birthday.month, kid.kid_birthday.day)
    )
    goodbyes = sorted([kid for kid in kids if (kid.get_alter()
                      and (kid.get_alter() > 14.8))], key=lambda kid: kid.get_alter())
    geburtstage = len(geburtstagskinder)
    eingecheckte_kids = kids.filter(anwesend=True).count()
    team = Profil.objects.filter(turnus=active_turnus).annotate(
        total_betreuerinnen_geld=Sum('betreuerinnen_geld__amount')
    )
    medikamente = [kid for kid in kids if kid.get_clean_drugs()]
    gesundheit = [kid for kid in kids if kid.get_clean_illness()]
    kids_attention = [kid for kid in kids if (
        kid.get_clean_drugs() or kid.get_clean_illness())]
    ersties = kids.filter(budo_erfahrung=False)
    ersties_count = ersties.count()
    einwöchige = kids.filter(turnus_dauer=1)
    einwöchige_count = einwöchige.count()
    notizen = Notizen.objects.filter(kinder__turnus=active_turnus)
    total_taschengeld = Geld.objects.filter(
        kinder__turnus=active_turnus).aggregate(Sum('amount'))['amount__sum'] or 0
    geld_transactions = Geld.objects.filter(
        kinder__turnus=active_turnus).order_by('-date_added')
    print("Debugging Geld transactions:")
    for transaction in geld_transactions:
        print(f"Transaction type: {type(transaction)}")
        print(f"Transaction dir: {dir(transaction)}")
    geld_eingezahlt = Geld.objects.filter(
        kinder__turnus=active_turnus, amount__gt=0).aggregate(Sum('amount'))['amount__sum'] or 0
    betreuerinnen_geld_gesamt = BetreuerinnenGeld.objects.aggregate(Sum('amount'))[
        'amount__sum'] or 0
    betreuerinnen_geld = BetreuerinnenGeld.objects.all()
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
        "goodbyes": goodbyes,
        "notizen": notizen,
        "total_taschengeld": total_taschengeld,
        "geld_transactions": geld_transactions,
        "geld_eingezahlt": geld_eingezahlt,
        "betreuerinnen_geld_gesamt": betreuerinnen_geld_gesamt,
        "betreuerinnen_geld": betreuerinnen_geld,
        "einwöchige": einwöchige,
        "einwöchige_count": einwöchige_count,
    }

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
