import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch
from django.forms import modelformset_factory
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.template import loader
from django.urls import reverse_lazy
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.views.generic import DetailView
from django.views.generic.edit import CreateView, UpdateView

from . import models
from .forms import MealChoiceForm, SchwerpunktForm
from .models import (
    Auslagerorte,
    Kinder,
    Meal,
    Profil,
    Schwerpunkte,
    SchwerpunktWahl,
    Schwerpunktzeit,
)
from .utils import (
    cache_user_profile,
    get_active_kid_or_404,
    get_active_turnus,
    get_turnus_data_optimized,
    parse_json_body,
    safe_get_object_or_404,
)


class SchwerpunkteUpdate(LoginRequiredMixin, UpdateView):
    model = Schwerpunkte
    form_class = SchwerpunktForm
    template_name = "schwerpunkt-form.html"

    def get_queryset(self):
        return Schwerpunkte.objects.filter(
            schwerpunktzeit__turnus=get_active_turnus(self.request)
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['turnus'] = get_active_turnus(self.request)
        return kwargs

    def get_context_data(self, **kwargs):
        profil = Profil.objects.get(user=self.request.user)
        active_turnus = profil.turnus
        schwerpunkte = Schwerpunkte.objects.filter(
            schwerpunktzeit__turnus=active_turnus)
        auslagerorte = Auslagerorte.objects.all()
        kids = models.Kinder.objects.filter(turnus=active_turnus)
        context = super().get_context_data(**kwargs)
        context['action'] = 'updaten'
        context['schwerpunkte'] = schwerpunkte
        context['auslagerorte'] = auslagerorte
        context['kids'] = kids
        return context

    def form_valid(self, form):
        messages.success(self.request, "Schwerpunkt upgedatet!")
        return super(SchwerpunkteUpdate, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy('schwerpunkt-detail', kwargs={'pk': self.object.pk})


class SchwerpunkteDetail(LoginRequiredMixin, DetailView):
    model = Schwerpunkte
    template_name = 'schwerpunkt-detail.html'
    context_object_name = 'schwerpunkt'

    def get_queryset(self):
        return Schwerpunkte.objects.filter(
            schwerpunktzeit__turnus=get_active_turnus(self.request)
        )

    def get_context_data(self, **kwargs):
        profil = Profil.objects.get(user=self.request.user)
        active_turnus = profil.turnus
        schwerpunkte = Schwerpunkte.objects.filter(
            schwerpunktzeit__turnus=active_turnus)
        auslagerorte = Auslagerorte.objects.all()
        kids = models.Kinder.objects.filter(turnus=active_turnus)
        context = super().get_context_data(**kwargs)
        meals_by_day = {}
        for meal in self.object.meals.all():
            if meal.day not in meals_by_day:
                meals_by_day[meal.day] = []
            meals_by_day[meal.day].append(meal)
        context['meals_by_day'] = meals_by_day
        context['schwerpunkte'] = schwerpunkte
        context['auslagerorte'] = auslagerorte
        context['kids'] = kids

        schwerpunkt = self.get_object()
        auslagerorte_data = [{
            'id': schwerpunkt.id,
            'name': schwerpunkt.swp_name,
            'koordinaten': schwerpunkt.ort.koordinaten if schwerpunkt.ort else '',
            'kind': 'schwerpunkt',
        }]

        try:
            if schwerpunkt.ort.name != "BuDo":
                budo_ort = Auslagerorte.objects.get(name="BuDo")
                auslagerorte_data.append({
                    'id': budo_ort.id,
                    'name': budo_ort.name,
                    'koordinaten': budo_ort.koordinaten,
                    'kind': 'auslagerorte',
                })
        except (Auslagerorte.DoesNotExist, AttributeError):
            pass

        context['orte_json'] = json.dumps({
            'orte': auslagerorte_data,
        })

        return context


class SchwerpunkteCreate(LoginRequiredMixin, CreateView):
    model = Schwerpunkte
    form_class = SchwerpunktForm
    template_name = 'schwerpunkt-form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['turnus'] = get_active_turnus(self.request)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'erstellen'
        return context

    def form_valid(self, form):
        messages.success(self.request, "Schwerpunkt hinzugefügt!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('schwerpunkt-detail', kwargs={'pk': self.object.pk})


class MealUpdate(LoginRequiredMixin, UpdateView):
    model = Schwerpunkte
    form_class = MealChoiceForm
    template_name = "swpmeals.html"

    def get_queryset(self):
        return Schwerpunkte.objects.filter(
            schwerpunktzeit__turnus=get_active_turnus(self.request)
        )

    def get_success_url(self):
        return reverse_lazy('schwerpunkt-detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        MealFormSet = modelformset_factory(Meal, form=MealChoiceForm, extra=0)
        if self.request.POST:
            data['meal_formset'] = MealFormSet(
                self.request.POST, queryset=Meal.objects.filter(schwerpunkt=self.object))
        else:
            data['meal_formset'] = MealFormSet(
                queryset=Meal.objects.filter(schwerpunkt=self.object))

        data['exclude_search'] = True
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        meal_formset = context['meal_formset']
        if meal_formset.is_valid():
            meal_formset.save()
            return redirect(self.get_success_url())
        return self.render_to_response(self.get_context_data(form=form))


@login_required
@cache_user_profile
def swp_dashboard(request):
    template = loader.get_template('swp-dashboard.html')

    if not request.user_profile:
        messages.error(
            request, "Profile not found. Please contact an administrator.")
        return redirect('dashboard')

    turnus_data = get_turnus_data_optimized(request.active_turnus)
    kids = turnus_data['kids']
    schwerpunkte = turnus_data['schwerpunkte']

    schwerpunkte_u = Schwerpunkte.objects.filter(
        schwerpunktzeit__turnus=request.active_turnus, schwerpunktzeit__woche='u'
    ).select_related('ort', 'schwerpunktzeit').prefetch_related('betreuende')

    schwerpunkte_data = []
    for swp in schwerpunkte:
        if swp.ort:
            schwerpunkte_data.append({
                'id': swp.id,
                'name': swp.swp_name,
                'koordinaten': swp.ort.koordinaten,
                'kind': 'schwerpunkt',
            })
    auslagerorte = turnus_data['auslagerorte']

    context = {
        "profil": request.user_profile,
        "kids": kids,
        "schwerpunkte": schwerpunkte,
        'orte_json': json.dumps({
            'orte': schwerpunkte_data,
        }),
        "auslagerorte": auslagerorte,
        "schwerpunkte_u": schwerpunkte_u,
    }

    return HttpResponse(template.render(context, request))


@login_required
def kitchen(request):
    template = loader.get_template('kitchen.html')
    profil = Profil.objects.get(user=request.user)
    active_turnus = profil.turnus
    team = Profil.objects.filter(turnus=active_turnus)
    kids = Kinder.objects.filter(turnus=active_turnus)
    schwerpunkte = Schwerpunkte.objects.filter(
        schwerpunktzeit__turnus=active_turnus)
    auslagerorte = Auslagerorte.objects.all()

    meal_types = ["breakfast", "lunch", "dinner"]
    meal_counts = {}

    for swp in schwerpunkte:
        week = swp.schwerpunktzeit.woche
        dauer = swp.schwerpunktzeit.dauer

        if week not in meal_counts:
            meal_counts[week] = {
                day: {
                    "breakfast": {"box": [], "budo": [], "warm": [], "kochportionen": 0},
                    "lunch": {"box": [], "budo": [], "warm": [], "kochportionen": 0},
                    "dinner": {"box": [], "budo": [], "warm": [], "kochportionen": 0}
                }
                for day in range(1, dauer + 1)
            }

        for meal in swp.meals.all():
            if meal.day <= dauer:
                kids_count = meal.get_kids_count()
                if meal.meal_choice:
                    meal_counts[week][meal.day][meal.meal_type][meal.meal_choice].append(
                        f"{swp.swp_name} ({kids_count})")
                    if meal.meal_choice in ["budo", "warm"]:
                        meal_counts[week][meal.day][meal.meal_type]["kochportionen"] += kids_count

    formatted_meal_counts = {}
    for week, week_data in meal_counts.items():
        formatted_meal_counts[week] = {}
        for day, meals in week_data.items():
            formatted_meal_counts[week][day] = {
                meal_type: {
                    'box': meals[meal_type].get('box', []),
                    'budo': meals[meal_type].get('budo', []),
                    'warm': meals[meal_type].get('warm', []),
                    'kochportionen': meals[meal_type].get('kochportionen', 0)
                }
                for meal_type in meal_types
            }

    context = {
        "profil": profil,
        "schwerpunkte": schwerpunkte,
        "auslagerorte": auslagerorte,
        "meal_counts": formatted_meal_counts,
        "kids": kids,
        "team": team,
        "meal_types": meal_types,
    }
    return HttpResponse(template.render(context, request))


@login_required
@never_cache
def swp_einteilung(request, week):
    profil = Profil.objects.get(user=request.user)
    active_turnus = profil.turnus
    schwerpunktzeit = Schwerpunktzeit.objects.get(
        turnus=active_turnus, woche=f"w{week}")

    kids = models.Kinder.objects.filter(turnus=active_turnus).prefetch_related(
        Prefetch('schwerpunkt_wahl',
                 queryset=SchwerpunktWahl.objects.filter(
                     schwerpunktzeit=schwerpunktzeit),
                 to_attr='wahl')
    ).prefetch_related(
        Prefetch('schwerpunkte',
                 queryset=Schwerpunkte.objects.filter(
                     schwerpunktzeit__woche=f"w{week}"),
                 to_attr='schwerpunkt')
    )

    schwerpunkte = Schwerpunkte.objects.filter(
        schwerpunktzeit__turnus=active_turnus, schwerpunktzeit__woche=f"w{week}")
    auslagerorte = Auslagerorte.objects.all()
    ungrouped_count = sum(1 for kid in kids if not kid.schwerpunkt)

    template = loader.get_template('swp-einteilung.html')
    context = {
        'kids': kids,
        'schwerpunkte': schwerpunkte,
        'auslagerorte': auslagerorte,
        'ungrouped_count': ungrouped_count,
        'week_number': week,
    }
    return HttpResponse(template.render(context, request))


@login_required
def swp_einteilung_w1(request):
    return swp_einteilung(request, 1)


@login_required
def swp_einteilung_w2(request):
    return swp_einteilung(request, 2)


@login_required
@cache_user_profile
@require_POST
@csrf_protect
def update_schwerpunkt_wahl(request):
    data = parse_json_body(request)
    if data is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    kid_id = data.get('kid_id')
    swp_id = data.get('swp_id')
    choice_rank = data.get('choice_rank')

    try:
        kid = get_active_kid_or_404(request, kid_id)
        schwerpunkt = safe_get_object_or_404(
            Schwerpunkte, id=swp_id, schwerpunktzeit__turnus=request.active_turnus)
        schwerpunktzeit = schwerpunkt.schwerpunktzeit

        schwerpunkt_wahl, created = SchwerpunktWahl.objects.get_or_create(
            kind=kid,
            schwerpunktzeit=schwerpunktzeit
        )

        if choice_rank is not None:
            if choice_rank == '1':
                kid.schwerpunkte.remove(
                    *kid.schwerpunkte.filter(schwerpunktzeit=schwerpunktzeit))
                schwerpunkt_wahl.erste_wahl = schwerpunkt
                kid.schwerpunkte.add(schwerpunkt)
            elif choice_rank == '2':
                schwerpunkt_wahl.zweite_wahl = schwerpunkt
            elif choice_rank == '3':
                schwerpunkt_wahl.dritte_wahl = schwerpunkt
        else:
            kid.schwerpunkte.remove(
                *kid.schwerpunkte.filter(schwerpunktzeit=schwerpunktzeit))
            kid.schwerpunkte.add(schwerpunkt)

        schwerpunkt_wahl.save()

        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
@cache_user_profile
@require_POST
@csrf_protect
def update_freunde(request):
    data = parse_json_body(request)
    if data is None:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    kid_id = data.get('kid_id')
    freunde = data.get('freunde')
    week = str(data.get('week', '1'))
    if week not in ('1', '2'):
        return JsonResponse(
            {'status': 'error', 'message': 'Week must be 1 or 2'},
            status=400,
        )

    try:
        kid = get_active_kid_or_404(request, kid_id)
        schwerpunkt_wahl = SchwerpunktWahl.objects.get(
            kind=kid,
            schwerpunktzeit__turnus=request.active_turnus,
            schwerpunktzeit__woche=f"w{week}",
        )
        schwerpunkt_wahl.freunde = freunde
        schwerpunkt_wahl.save()
        return JsonResponse({'status': 'success'})
    except (Kinder.DoesNotExist, SchwerpunktWahl.DoesNotExist):
        return JsonResponse({'status': 'error', 'message': 'Kid or SchwerpunktWahl not found'})
