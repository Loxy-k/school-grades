from django.apps import AppConfig


class GradesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'grades'
    
    def ready(self):
        # Import signals here
        try:
            import grades.signals
        except ImportError:
            pass
