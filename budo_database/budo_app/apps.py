from django.apps import AppConfig


class BudoAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'budo_app'

    def ready(self):
        from .image_formats import register_heif_opener

        register_heif_opener()
