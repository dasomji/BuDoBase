from django.core.exceptions import PermissionDenied


def is_product_admin(user):
    """Return whether a user may administer product-wide, cross-Turnus data."""
    return bool(user.is_authenticated and user.is_superuser)


def require_product_admin(user, message="Product admin access denied."):
    if not is_product_admin(user):
        raise PermissionDenied(message)
