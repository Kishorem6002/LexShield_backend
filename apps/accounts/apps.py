from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'

    def ready(self):
        # Pre-warm ML models in background thread so first request is instant.
        # Runs once when Django finishes loading — does NOT block startup.
        import threading

        def _warmup():
            try:
                from services.moderation.ml_adapter import get_model_manager
                mgr = get_model_manager()
                mgr.get_text_model()
                mgr.get_image_model()
                print('[Civility] ML models pre-warmed and ready.')
            except Exception as e:
                print(f'[Civility] ML warmup skipped: {e}')

        t = threading.Thread(target=_warmup, daemon=True, name='ml-warmup')
        t.start()
