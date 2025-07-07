from django.apps import AppConfig, apps


class OpsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ops'

    def ready(self):
        from auditlog.registry import auditlog
        # Core models
        app_models = apps.get_app_config(self.label).get_models()
        for model in app_models:
            auditlog.register(model)