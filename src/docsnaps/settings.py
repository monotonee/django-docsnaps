import django.conf.settings

DOCSNAPS_REQUEST_TIMEOUT = getattr(
    django.conf.settings,
    'DOCSNAPS_REQUEST_TIMEOUT',
    10)
