from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class ProfileAwareModelBackend(ModelBackend):
    """Load request-scoped profile data with the authenticated user."""

    def get_user(self, user_id):
        user_model = get_user_model()
        try:
            user = user_model._default_manager.select_related(
                "profil", "profil__selected_turnus",
            ).get(pk=user_id)
        except user_model.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None
