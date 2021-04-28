# Django settings for devel env.

from tcms.settings.common import *

# Debug settings
DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": SUPPORTED_DB_ENGINES[DB_ENGINE],
        "NAME": env.get("NITRATE_DB_NAME", "nitrate"),
        "USER": env.get("NITRATE_DB_USER", "root"),
        "PASSWORD": env.get("NITRATE_DB_PASSWORD", ""),
        "HOST": env.get("NITRATE_DB_HOST", ""),
        "PORT": env.get("NITRATE_DB_PORT", ""),
    },
}

SECRET_KEY = "secret-key-for-dev-only"

# django-debug-toolbar settings
MIDDLEWARE += ("debug_toolbar.middleware.DebugToolbarMiddleware",)

INSTALLED_APPS += ("debug_toolbar",)

DEBUG_TOOLBAR_CONFIG = {"INTERCEPT_REDIRECTS": False}

FILE_UPLOAD_DIR = os.path.join(TCMS_ROOT_PATH, "..", "uploads")

ASYNC_TASK = "DISABLED"
