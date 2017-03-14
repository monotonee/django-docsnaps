import os.path

import django.apps


class AppConfig(django.apps.AppConfig):
    name = 'django_docsnaps'
    path = os.path.dirname(__file__)
    verbose_name = 'document snapshots'
