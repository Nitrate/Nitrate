from tcms.settings.common import *

# Test uses sqlite as the default database backend.

DB_ENGINE = env.get('NITRATE_DB_ENGINE', 'sqlite')

DATABASES = {
    'default': {
        'ENGINE': SUPPORTED_DB_ENGINES[DB_ENGINE],
        'NAME': env.get('NITRATE_DB_NAME', ''),
        'USER': env.get('NITRATE_DB_USER', ''),
        'PASSWORD': env.get('NITRATE_DB_PASSWORD', ''),
        'HOST': env.get('NITRATE_DB_HOST', ''),
        'PORT': env.get('NITRATE_DB_PORT', ''),
    },
}

if DB_ENGINE == 'mysql':
    DATABASES['default']['TEST'] = {'CHARSET': 'utf8mb4'}
elif DB_ENGINE == 'pgsql':
    DATABASES['default']['TEST'] = {'CHARSET': 'utf8'}


ASYNC_TASK = 'DISABLED'
LISTENING_MODEL_SIGNAL = False

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '[%(asctime)s] %(levelname)s %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'console':{
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}
