from django.db.models import Sum

from budo_app.models import BetreuerinnenGeld, Geld, Kinder, Notizen, Profil


def build_dashboard_context(profile, active_turnus):
    kids = Kinder.objects.filter(turnus=active_turnus).select_related(
        'turnus', 'spezial_familien')

    geburtstagskinder = sorted(
        [kid for kid in kids if kid.is_birthday_during_turnus()],
        key=lambda kid: (kid.kid_birthday.month, kid.kid_birthday.day)
    )
    goodbyes = sorted(
        [kid for kid in kids if kid.get_alter() and kid.get_alter() > 14.8],
        key=lambda kid: kid.get_alter()
    )
    medikamente = [kid for kid in kids if kid.get_clean_drugs()]
    gesundheit = [kid for kid in kids if kid.get_clean_illness()]
    kids_attention = [
        kid for kid in kids if kid.get_clean_drugs() or kid.get_clean_illness()
    ]
    ersties = kids.filter(budo_erfahrung=False)
    einwoechige = kids.filter(turnus_dauer=1)

    return {
        "profil": profile,
        "kids": kids,
        "kids_zug_anreise_count": kids.filter(zug_anreise=True).count(),
        "kids_zug_abreise_count": kids.filter(zug_abreise=True).count(),
        "male_kids_count": kids.filter(sex="männlich").count(),
        "female_kids_count": kids.filter(sex="weiblich").count(),
        "diverse_kids_count": kids.exclude(sex__in=["männlich", "weiblich"]).count(),
        "kids_mit_budo_erfahrung": kids.filter(budo_erfahrung=True).count(),
        "geburtstagskinder": geburtstagskinder,
        "geburtstage": len(geburtstagskinder),
        "eingecheckte_kids": kids.filter(anwesend=True).count(),
        "anzahl_kids": kids.count(),
        "team": Profil.objects.filter(turnus=active_turnus).annotate(
            total_betreuerinnen_geld=Sum('betreuerinnen_geld__amount')
        ).select_related('user'),
        "medikamente": medikamente,
        "gesundheit": gesundheit,
        "kids_attention": kids_attention,
        "ersties": ersties,
        "ersties_count": ersties.count(),
        "goodbyes": goodbyes,
        "notizen": Notizen.objects.filter(
            kinder__turnus=active_turnus
        ).select_related('kinder', 'added_by'),
        "total_taschengeld": Geld.objects.filter(
            kinder__turnus=active_turnus
        ).aggregate(Sum('amount'))['amount__sum'] or 0,
        "geld_transactions": Geld.objects.filter(
            kinder__turnus=active_turnus
        ).select_related('kinder', 'added_by').order_by('-date_added'),
        "geld_eingezahlt": Geld.objects.filter(
            kinder__turnus=active_turnus, amount__gt=0
        ).aggregate(Sum('amount'))['amount__sum'] or 0,
        "betreuerinnen_geld_gesamt": BetreuerinnenGeld.objects.aggregate(
            Sum('amount')
        )['amount__sum'] or 0,
        "betreuerinnen_geld": BetreuerinnenGeld.objects.all(),
        "einwöchige": einwoechige,
        "einwöchige_count": einwoechige.count(),
    }
