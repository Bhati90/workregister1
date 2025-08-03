
from django.apps import AppConfig

class RegistrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'registration'
    verbose_name = 'Labor Registration System'

    def ready(self):
        # Import signals if you have any
        # import registration.signals
        pass