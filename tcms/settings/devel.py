# Django settings for devel env.

from __future__ import absolute_import

from tcms.settings.common import *

# Debug settings
DEBUG = True

# Database settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'nitrate',
        'USER': 'root',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

# django-debug-toolbar settings
MIDDLEWARE += (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

INSTALLED_APPS += (
    'debug_toolbar',
    'django_extensions',
)

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False
}

FILE_UPLOAD_DIR = os.path.join(TCMS_ROOT_PATH, '..', 'uploads')

ASYNC_TASK = 'DISABLED'
