"""
A module of app-specific settings and their respective defaults.

"""

import django.conf.settings


DJANGO_DOCSNAPS_REQUEST_TIMEOUT = getattr(
    django.conf.settings,
    'DJANGO_DOCSNAPS_REQUEST_TIMEOUT',
    10)
