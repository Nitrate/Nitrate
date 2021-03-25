# Django settings for product env.

from django.core.exceptions import ImproperlyConfigured

from tcms.settings.common import *  # noqa

environ = os.environ

# Debug settings
DEBUG = False
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    "default": {
        "ENGINE": SUPPORTED_DB_ENGINES[DB_ENGINE],
        "NAME": environ.get("NITRATE_DB_NAME", "nitrate"),
        "USER": environ.get("NITRATE_DB_USER", "nitrate"),
        "PASSWORD": environ.get("NITRATE_DB_PASSWORD", "nitrate"),
        "HOST": environ.get("NITRATE_DB_HOST", ""),
        "PORT": environ.get("NITRATE_DB_PORT", ""),
    },
}

SECRET_KEY = os.environ.get("NITRATE_SECRET_KEY", "")

if not SECRET_KEY:
    raise ImproperlyConfigured(
        "Environment variable NITRATE_SECRET_KEY must be set to provide a "
        "unique secret key to the Django's SECRET_KEY"
    )

AUTHENTICATION_BACKENDS = ("django.contrib.auth.backends.ModelBackend",)

TEMPLATES[0].update(
    {
        "DIRS": ["/usr/share/nitrate/templates"],
    }
)


# Set the default send mail address
EMAIL_HOST = "smtp.example.com"
EMAIL_FROM = "noreply@example.com"

# Site-specific messages

# added for nitrate3.4 compatibility
DEFAULT_GROUPS = ["default"]

# You can add a help link on the footer of home page as following format:
# ('http://foo.com', 'foo')
FOOTER_LINKS = (
    ("https://nitrate.readthedocs.io/en/latest/api/xmlrpc.html", "XML-RPC Service"),
    ("https://nitrate.readthedocs.io/en/latest/guide.html", "User Guide"),
)

# admin settings
ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

try:
    from nitrate_custom_conf import *
except ModuleNotFoundError:
    import sys

    print("No custom config module is importable.", file=sys.stderr)
    print(
        "If the custom config module is expected to be importable, "
        "please check whether the directory containing the module is added "
        "to the PYTHONPATH already.",
        file=sys.stderr,
    )
