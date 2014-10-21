DEBUG = True

SECRET_KEY = 'ItsSekret'

USE_TZ = True

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