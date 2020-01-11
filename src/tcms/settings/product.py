# Django settings for product env.

from tcms.settings.common import *  # noqa

# Debug settings
DEBUG = False
TEMPLATE_DEBUG = DEBUG

# Database settings
DATABASES = {
    'default': {
        'ENGINE': SUPPORTED_DB_ENGINES[DB_ENGINE],
        'NAME': env.get('NITRATE_DB_NAME', 'nitrate'),
        'USER': env.get('NITRATE_DB_USER', 'nitrate'),
        'PASSWORD': env.get('NITRATE_DB_PASSWORD', 'nitrate'),
        'HOST': env.get('NITRATE_DB_HOST', ''),
        'PORT': env.get('NITRATE_DB_PORT', ''),
    },
}

# For Kerberos authentication, uncomment out RemoteUserMiddleware.
# MIDDLEWARE += (
#    'django.contrib.auth.middleware.RemoteUserMiddleware',
# )

# Remote kerberos authentication backends
# AUTHENTICATION_BACKENDS = (
#    'tcms.auth.backends.ModAuthKerbBackend',
# )

# To enable database routers for read/write separation.
# DATABASE_ROUTERS = ['tcms.core.tcms_router.RWRouter']

# Kerberos realm
# KRB5_REALM = 'EXAMPLE.COM'

# User authentication by Bugzilla settings
# BUGZILLA_XMLRPC_URL = 'https://bugzilla.example.com/xmlrpc.cgi'


TEMPLATES[0].update({
    'DIRS': ['/usr/share/nitrate/templates'],
})

# Set the default send mail address
EMAIL_HOST = 'smtp.example.com'
EMAIL_FROM = 'noreply@example.com'

# Site-specific messages

# First run - to determine if it needs to prompt user or not.
FIRST_RUN = False

# You can add a help link on the footer of home page as following format:
# ('http://foo.com', 'foo')
FOOTER_LINKS = (
    ('https://nitrate.readthedocs.io/en/latest/api/xmlrpc.html', 'XML-RPC Service'),
    ('https://nitrate.readthedocs.io/en/latest/guide.html', 'User Guide'),
)

# added for nitrate3.4 compatibility
DEFAULT_GROUPS = ['default']

# admin settings
ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

DEFAULT_PAGE_SIZE = 100
