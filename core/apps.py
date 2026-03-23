from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'
    # Phase 1: core is kept only so its migration history remains intact
    # for the data migration in allocation/migrations/0002.
    # Do NOT add new models here. Will be removed in Phase 2.
