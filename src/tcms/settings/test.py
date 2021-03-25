from tcms.settings.common import *

# Test uses sqlite as the default database backend.

DB_ENGINE = env.get("NITRATE_DB_ENGINE", "sqlite")

db_host = (
    env.get("NITRATE_DB_HOST", "")
    or
    # These three variables will be set by tox-docker if use to run tests with
    # specific database engine.
    env.get("TESTDB_MYSQL_HOST", "")
    or env.get("TESTDB_MARIADB_HOST", "")
    or env.get("TESTDB_POSTGRES_HOST", "")
)

DATABASES = {
    "default": {
        "ENGINE": SUPPORTED_DB_ENGINES[DB_ENGINE],
        "NAME": env.get("NITRATE_DB_NAME", ""),
        "USER": env.get("NITRATE_DB_USER", ""),
        "PASSWORD": env.get("NITRATE_DB_PASSWORD", ""),
        "HOST": db_host,
        "PORT": env.get("NITRATE_DB_PORT", ""),
    },
}

if DB_ENGINE == "mysql":
    DATABASES["default"]["TEST"] = {"CHARSET": "utf8mb4"}
elif DB_ENGINE == "pgsql":
    DATABASES["default"]["TEST"] = {"CHARSET": "utf8"}


SECRET_KEY = "key-for-test"

ASYNC_TASK = "DISABLED"
LISTENING_MODEL_SIGNAL = False

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"
        },
        "simple": {"format": "[%(asctime)s] %(levelname)s %(message)s"},
    },
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
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
    },
}
