"""
Run tests by directly invoking this file from the Python interpreter.

Running tests after setting up a skeleton Django environment allows for the
use of Django testing tools.

See:
    https://docs.djangoproject.com/en/dev/topics/testing/advanced/#using-the-django-test-runner-to-test-reusable-applications

"""

import os
import sys

import django
from django.conf import settings
from django.test.utils import get_runner


if __name__ == '__main__':
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2)
    failures = test_runner.run_tests(['tests'])
    sys.exit(bool(failures))
