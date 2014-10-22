django-messaging-subscription
=============================

A RESTful API for managing messaging content, subscriptions and sending via Vumi-go

::

    $ virtualenv ve
    $ source ve/bin/activate
    (ve)$ pip install -r requirements.txt
    (ve)$ pip install -r requirements-dev.txt
    (ve)$ py.test --ds=testsettings subscription/tests.py --cov=subscription
