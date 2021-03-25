# -*- coding: utf-8 -*-

import os.path

TCMS_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

NITRATE_VERSION = "4.4"

DEBUG = True

# Administrators error report email settings
ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

env = os.environ
DB_ENGINE = env.get("NITRATE_DB_ENGINE", "mysql")

SUPPORTED_DB_ENGINES = {
    "mysql": "django.db.backends.mysql",
    "sqlite": "django.db.backends.sqlite3",
    "pgsql": "django.db.backends.postgresql",
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.",
        "NAME": "",
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    },
    # Enable these settings for slave databases
    # First slave DB for reading
    # 'slave_1': {
    #     'ENGINE': 'django.db.backends.',
    #     'NAME': '',
    #     'USER': '',
    #     'PASSWORD': '',
    #     'HOST': '',
    #     'PORT': '',
    # },
    # Second slave DB for reporting, optional
    # 'slave_report': {
    #     'ENGINE': 'django.db.backends.',
    #     'NAME': '',
    #     'USER': '',
    #     'PASSWORD': '',
    #     'HOST': '',
    #     'PORT': '',
    # }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ["*"]

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = "UTC"

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = "en-us"

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = False

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ""

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ""

LOGIN_URL = "nitrate-login"
LOGIN_REDIRECT_URL = "user-profile-redirect"
LOGOUT_REDIRECT_URL = "nitrate-login"

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = "/usr/share/nitrate/static/"

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = "/static/"

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(TCMS_ROOT_PATH, "static").replace("\\", "/"),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(TCMS_ROOT_PATH, "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "debug": True,
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                # Added for Nitrate
                "django.template.context_processors.request",
                "tcms.core.context_processors.request_contents_processor",
                "tcms.core.context_processors.settings_processor",
            ],
        },
    },
]


MIDDLEWARE = (
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
)

ROOT_URLCONF = "tcms.urls"

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = "tcms.wsgi.application"

CSRF_USE_SESSIONS = True

INSTALLED_APPS = (
    "django.contrib.admin",
    "django.contrib.admindocs",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "django_comments",
    "kobo.django.xmlrpc",
    "tinymce",
    "tcms.auth.apps.AppConfig",
    "tcms.comments.apps.AppConfig",
    "tcms.linkreference",
    "tcms.logs",
    "tcms.issuetracker",
    "tcms.management",
    "tcms.profiles",
    "tcms.testcases",
    "tcms.testplans",
    "tcms.testruns",
    "tcms.xmlrpc.apps.AppConfig",
    "tcms.report",
    # core app must be here in order to use permissions created during creating
    # modules for above apps.
    "tcms.core.apps.AppConfig",
)

SESSION_SERIALIZER = "django.contrib.sessions.serializers.JSONSerializer"

#
# Default apps settings
#

# Define the custom comment app
# http://docs.djangoproject.com/en/dev/ref/contrib/comments/custom/

COMMENTS_APP = "tcms.comments"  # 'nitrate_comments'

#
# XML-RPC interface settings
#
# XML-RPC methods

XMLRPC_METHODS = {
    "TCMS_XML_RPC": (
        ("tcms.xmlrpc.api.auth", "Auth"),
        ("tcms.xmlrpc.api.build", "Build"),
        ("tcms.xmlrpc.api.env", "Env"),
        ("tcms.xmlrpc.api.product", "Product"),
        ("tcms.xmlrpc.api.testcase", "TestCase"),
        ("tcms.xmlrpc.api.testcaserun", "TestCaseRun"),
        ("tcms.xmlrpc.api.testcaseplan", "TestCasePlan"),
        ("tcms.xmlrpc.api.testopia", "Testopia"),
        ("tcms.xmlrpc.api.testplan", "TestPlan"),
        ("tcms.xmlrpc.api.testrun", "TestRun"),
        ("tcms.xmlrpc.api.user", "User"),
        ("tcms.xmlrpc.api.version", "Version"),
        ("tcms.xmlrpc.api.tag", "Tag"),
    ),
}

XMLRPC_TEMPLATE = "xmlrpc.html"

# Cache backend
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# Needed by django.core.context_processors.debug:
# See http://docs.djangoproject.com/en/dev/ref/templates/api/#django-core-context-processors-debug
INTERNAL_IPS = ("127.0.0.1",)

AUTHENTICATION_BACKENDS = ("django.contrib.auth.backends.ModelBackend",)

# Config for enabled authentication backend set in AUTHENTICATION_BACKENDS
ENABLED_AUTH_BACKENDS = {
    # Generally, only one backend requiring username and password is enabled,
    # for example a backend that authenticates a user from a LDAP, or a backend
    # that authenticates a user against database user info.
    # If no such kind of backend is enabled, for example RemoteUserBackend is
    # enabled to work with Web server that authenticates users actually, just
    # omit this config.
    "USERPWD": {
        # Whether to show user registration link.
        "ALLOW_REGISTER": True,
        # No other configs are defined at this moment.
    },
    # Allow to login some social authentication backend. This works by enabling
    # social-auth-app-django.
    # Add following example mapping to enable supported social authentication
    # backends. Each of the list is a mapping to indicate the backend name,
    # what text should be displayed in login webpage, and optional value of
    # title attribute of the link.
    # The order of backends matters. Login URLs will display in the order of
    # the given backends.
    #
    # 'SOCIAL': [
    #     {
    #         'backend': 'fedora',
    #         'label': 'Fedora',
    #         'title': 'Login with Fedora account',
    #     },
    # ]
    # No other key/value pairs are supported so far.
}

#
# Mail settings
#
# Set the default send mail address
# See http://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_HOST = ""
EMAIL_PORT = 25
EMAIL_FROM = "noreply@foo.com"
EMAIL_SUBJECT_PREFIX = "[TCMS] "

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"
        },
        "simple": {"format": "[%(asctime)s] %(levelname)s %(message)s"},
        "xmlrpc_log": {"format": '[%(asctime)s] %(levelname)s XMLRPC %(process)d "%(message)s"'},
    },
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "xmlrpc": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "xmlrpc_log",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["mail_admins"],
            "level": "ERROR",
            "propagate": True,
        },
        "nitrate.xmlrpc": {
            "handlers": ["xmlrpc"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}

LOCALE_PATHS = (os.path.join(TCMS_ROOT_PATH, "locale"),)


# Site-specific messages

EMAILS_FOR_DEBUG = []

# Values: DISABLED, THREADING, CELERY
ASYNC_TASK = "DISABLED"

CELERY_BROKER_URL = "redis://"
# Celery worker settings
CELERY_TASK_IGNORE_RESULT = True

# Maximum upload file size, default set to 5MB.
# 2.5MB - 2621440
# 5MB - 5242880
# 10MB - 10485760
# 20MB - 20971520
# 50MB - 5242880
# 100MB 104857600
# 250MB - 214958080
# 500MB - 429916160
MAX_UPLOAD_SIZE = 5242880

# The site can supply optional "message of the day" style banners, similar to
# /etc/motd. They are fragments of HTML.

# This if set, is shown on the login/registration screens.
# MOTD_LOGIN = ''

# The URLS will be list in footer
# Example:
# FOOTER_LINKS = (
#   ('mailto:nitrate-dev-list@example.com', 'Contact Us'),
#   ('mailto:nitrate-admin@example.com', 'Request Permission'),
#   ('http://foo.com', 'foo')
# )
FOOTER_LINKS = ()

# Attachment file download path
# it could be specified to a different out of MEDIA_URL
# FILE_UPLOAD_DIR = path.join(MEDIA_DIR, 'uploads').replace('\\','/'),
FILE_UPLOAD_DIR = "/var/nitrate/uploads"

#
# Authentication backend settings
#
# Required by bugzilla authentication backend
# BUGZILLA_XMLRPC_URL = 'https://bugzilla.example.com/xmlrpc.cgi'

# Turn on/off listening signals sent by models.
LISTENING_MODEL_SIGNAL = True

# Kerberos settings
# Required by kerberos authentication backend
KRB5_REALM = ""

# user guide url:
USER_GUIDE_URL = ""

TESTOPIA_XML_VERSION = "1.1"
