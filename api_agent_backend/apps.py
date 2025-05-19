from django.apps import AppConfig

class ApiAgentBackendConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api_agent_backend'
    
    def ready(self):
        import api_agent_backend.signals  
