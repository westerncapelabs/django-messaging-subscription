django-messaging-subscription
================================

A RESTful API for managing messaging content, subscriptions and sending
via Vumi-go


::

    $ virtualenv ve
    $ source ve/bin/activate
    (ve)$ pip install -r requirements.txt
    (ve)$ pip install -r requirements-dev.txt
    (ve)$ py.test --ds=testsettings subscription/tests.py --cov=subscription


Configuration
-------------------------------

The following configuration (with dummy values replaced by real ones) needs to
be added to ``settings.py`` to configure this app:

.. code-block:: python

    INSTALLED_APPS = [
        # Usual Django stuff plus
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

    CELERY_ACCEPT_CONTENT = ['pickle']
    CELERY_TASK_SERIALIZER = 'pickle'
    CELERY_RESULT_SERIALIZER = 'pickle'
    CELERY_ALWAYS_EAGER = DEBUG
    SUBSCRIPTION_SEND_INITIAL_DELAYED = 1800 # optional delay in seconds
    SUBSCRIPTION_MULTIPART_BOUNDARY = "-------"


Release Notes
------------------------------
0.7.1 - 2016-05-20 - Pin and bump of dependency versions
0.7.0 - 2015-05-06 - Added support for firing metrics on completion of sets
0.6.0 - 2015-01-13 - Added support for default schedules on message sets for auto
transition
