"""
A module of app-specific settings and defaults.

"""

import django.conf.settings


DJANGO_DOCSNAPS_REQUEST_TIMEOUT = getattr(
    django.conf.settings,
    'DJANGO_DOCSNAPS_REQUEST_TIMEOUT',
    10)
