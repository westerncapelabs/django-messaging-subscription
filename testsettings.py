import os
import djcelery

DEBUG = True

djcelery.setup_loader()

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))


def abspath(*args):
    """convert relative paths to absolute paths relative to PROJECT_ROOT"""
    return os.path.join(PROJECT_ROOT, *args)

SECRET_KEY = 'ItsSekret'

USE_TZ = True

SITE_ID = 1

MEDIA_ROOT = abspath('media')

MEDIA_URL = '/media/'

STATIC_ROOT = abspath('static')

STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'subscriptionstore.db',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    # Third-party apps
    'south',
    'tastypie',
    'djcelery',
    # Us
    'subscription'
]

VUMI_GO_ACCOUNT_KEY = "replaceme"
VUMI_GO_CONVERSATION_KEY = "replaceme"
VUMI_GO_ACCOUNT_TOKEN = "replaceme"

ROOT_URLCONF = 'subscription.urls'

CELERY_ACCEPT_CONTENT = ['pickle']
CELERY_TASK_SERIALIZER = 'pickle'
CELERY_RESULT_SERIALIZER = 'pickle'
CELERY_ALWAYS_EAGER = True

SUBSCRIPTION_SEND_INITIAL_DELAYED = 0
SUBSCRIPTION_MULTIPART_BOUNDARY = "-------"
SUBSCRIPTION_NOOP_KEYWORD = "SKIPSEND"
