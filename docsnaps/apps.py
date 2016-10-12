import os.path

from django.apps import AppConfig


class DocsnapsConfig(AppConfig):
    name = 'docsnaps'
    path = os.path.dirname(__file__)
    verbose_name = 'document snapshots'
