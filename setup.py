from setuptools import setup, find_packages

setup(
    name="django-messaging-subscription",
    version="0.7.0",
    url="https://github.com/westerncapelabs/django-messaging-subscription",
    license='BSD',
    description=(
        "A RESTful API for managing messaging content, subscriptions and sending via Vumi-go"),
    long_description=open('README.rst', 'r').read(),
    author='Western Cape Labs',
    author_email='devops@westerncapelabs.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Django',
        'django-tastypie',
        'South',
        'gunicorn==19.0.0',
        'django-celery==3.1.10',
        'go-http==0.1.1',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Networking',
    ],
)
