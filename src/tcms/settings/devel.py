# Django settings for devel env.

from tcms.settings.common import *

# Debug settings
DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': SUPPORTED_DB_ENGINES[DB_ENGINE],
        'NAME': env.get('NITRATE_DB_NAME', 'nitrate'),
        'USER': env.get('NITRATE_DB_USER', 'root'),
        'PASSWORD': env.get('NITRATE_DB_PASSWORD', ''),
        'HOST': env.get('NITRATE_DB_HOST', ''),
        'PORT': env.get('NITRATE_DB_PORT', ''),
    },
}

# django-debug-toolbar settings
MIDDLEWARE += (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

INSTALLED_APPS += (
    'debug_toolbar',
    'django_extensions',

    'social_django',
)

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False
}

FILE_UPLOAD_DIR = os.path.join(TCMS_ROOT_PATH, '..', 'uploads')

ASYNC_TASK = 'DISABLED'

ENABLED_AUTH_BACKENDS = {
    # Generally, only one backend requiring username and password is enabled,
    # for example a backend that authenticates a user from a LDAP, or a backend
    # that authenticates a user against database user info.
    # If no such kind of backend is enabled, for example RemoteUserBackend is
    # enabled to work with Web server that authenticates users actually, just
    # omit this config.
    'USERPWD': {
        # Whether to show user registration link.
        'ALLOW_REGISTER': True,
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
    'SOCIAL': [
        {
            'backend': 'fedora',
            'label': 'Fedora',
            'title': 'Login with Fedora account',
        },
        {
            'backend': 'gitlab',
            'label': 'GitLab',
            'title': 'Login with GitLab account',
        },
        {
            'backend': 'github',
            'label': 'Github',
            'title': 'Login with Github account',
        },
    ]

    # No other key/value pairs are supported so far.
}

AUTHENTICATION_BACKENDS = (
    'social_core.backends.fedora.FedoraOpenId',
    'django.contrib.auth.backends.ModelBackend',
)
