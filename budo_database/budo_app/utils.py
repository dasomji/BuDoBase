from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from .models import Profil, Kinder, Schwerpunkte, Auslagerorte, Turnus


def get_user_profile(user):
    """
    Get user profile without caching.
    """
    try:
        profile = Profil.objects.select_related(
            'user', 'turnus').get(user=user)
        return profile
    except Profil.DoesNotExist:
        return None


def get_turnus_data_optimized(turnus):
    """
    Get optimized queryset for turnus-related data with proper select_related and prefetch_related.
    Returns a dictionary with commonly needed data for a turnus.
    """
    if not turnus:
        return {
            'kids': Kinder.objects.none(),
            'schwerpunkte': Schwerpunkte.objects.none(),
            'auslagerorte': Auslagerorte.objects.none(),
        }

    kids = Kinder.objects.filter(turnus=turnus).select_related(
        'turnus', 'spezial_familien'
    ).prefetch_related(
        'schwerpunkte', 'notizen', 'geld'
    ).order_by('kid_vorname')

    schwerpunkte = Schwerpunkte.objects.filter(
        schwerpunktzeit__turnus=turnus
    ).select_related(
        'ort', 'schwerpunktzeit'
    ).prefetch_related(
        'betreuende', 'swp_kinder', 'meals'
    )

    auslagerorte = Auslagerorte.objects.all().prefetch_related(
        'schwerpunkte_set', 'images', 'auslagernotizen'
    )

    return {
        'kids': list(kids),
        'schwerpunkte': list(schwerpunkte),
        'auslagerorte': list(auslagerorte),
    }


def safe_get_object(model_class, **kwargs):
    """
    Safely get an object with proper exception handling.
    Returns the object or None if not found.
    """
    try:
        return model_class.objects.get(**kwargs)
    except model_class.DoesNotExist:
        return None
    except model_class.MultipleObjectsReturned:
        # Return the first object if multiple found
        return model_class.objects.filter(**kwargs).first()


def safe_get_object_or_404(model_class, **kwargs):
    """
    Safely get an object with proper exception handling.
    Returns the object or raises Http404 if not found.
    """
    return get_object_or_404(model_class, **kwargs)
