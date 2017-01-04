SECRET_KEY = 'fake-key'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': '127.0.0.1',
        'PASSWORD': 'tester',
        'PORT': '49152',
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
