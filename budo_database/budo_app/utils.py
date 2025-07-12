from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from functools import wraps
from .models import Profil, Kinder, Schwerpunkte, Auslagerorte


def get_cached_user_profile(user):
    """
    Get user profile with caching to avoid repeated database queries.
    Cache key is based on user ID and profile's last modified time.
    """
    cache_key = f"user_profile_{user.id}"
    cached_profile = cache.get(cache_key)

    if cached_profile is None:
        try:
            profile = Profil.objects.select_related(
                'user', 'turnus').get(user=user)
            # Cache for 5 minutes
            cache.set(cache_key, profile, 300)
            return profile
        except Profil.DoesNotExist:
            return None

    return cached_profile


def invalidate_user_profile_cache(user):
    """Invalidate cached user profile when profile is updated."""
    cache_key = f"user_profile_{user.id}"
    cache.delete(cache_key)


def cache_user_profile(view_func):
    """
    Decorator to automatically inject cached user profile into view context.
    Adds 'user_profile' and 'active_turnus' to the view's context.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            profile = get_cached_user_profile(request.user)
            request.user_profile = profile
            request.active_turnus = profile.turnus if profile else None
        else:
            request.user_profile = None
            request.active_turnus = None
        return view_func(request, *args, **kwargs)
    return wrapper


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

    # Cache key based on turnus ID
    cache_key = f"turnus_data_{turnus.id}"
    cached_data = cache.get(cache_key)

    if cached_data is None:
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

        cached_data = {
            'kids': list(kids),
            'schwerpunkte': list(schwerpunkte),
            'auslagerorte': list(auslagerorte),
        }

        # Cache for 10 minutes
        cache.set(cache_key, cached_data, 600)

    return cached_data


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
