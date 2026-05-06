from django.apps import AppConfig

class ArchesIdGeneratorConfig(AppConfig):
    name = "arches_id_generator"
    verbose_name = "Arches ID Generator"
    is_arches_application = True
    
    def ready(self):
        from arches_id_generator import signals  # noqa: F401
        