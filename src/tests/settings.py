"""
See:
    https://docs.djangoproject.com/en/1.10/topics/testing/advanced/#using-the-django-test-runner-to-test-reusable-applications

"""
SECRET_KEY = 'fake-key'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': '127.0.0.1',
        'PASSWORD': 'tester',
        'PORT': '3306',
        'USER': 'tester',
    }
}

# DATABASE_ROUTERS = [
    # 'docsnaps.routers.Router'
# ]

INSTALLED_APPS = [
    'docsnaps.apps.DocsnapsConfig',
    'tests'
]
