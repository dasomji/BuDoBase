from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied


def is_product_admin(user):
    """Return whether a user may administer product-wide, cross-Turnus data."""
    return bool(user.is_authenticated and user.is_superuser)


def require_product_admin(user, message="Product admin access denied."):
    if not is_product_admin(user):
        raise PermissionDenied(message)


def is_locked_product_admin(user):
    """Read persisted product-admin authority after its User row is locked."""
    return get_user_model().objects.filter(pk=user.pk, is_superuser=True).exists()


def require_locked_product_admin(user, message="Product admin access denied."):
    """Fail closed when locked, persisted product-admin authority is absent."""
    if not is_locked_product_admin(user):
        raise PermissionDenied(message)
