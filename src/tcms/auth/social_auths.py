# -*- coding: utf-8 -*-

# Additional configuration for displaying social login information.
# This is a mapping from social authentication backend name to the login information.
# Currently, login information has properties:
# - icon: Nitrite uses FontAwesome to display social login logo. The ``icon``
#         is the icon name, which is used to construct class name, e.g. fa-fedora
# - size: the icon size to display. It defaults to 3x, that is fa-3x generated
#         in final template eventually.

SOCIAL_AUTHS_CONFIG = {
    'fedora': {
        'icon': 'fedora',
        'icon_size': '3x',
    },
    'github': {
        'icon': 'github',
        'icon_size': '3x',
    },
    'gitlab': {
        'icon': 'gitlab',
        'icon_size': '3x',
    },
    'twitter': {
        'icon': 'twitter',
        'icon_size': '3x',
    },
    'google': {
        'icon': 'google',
        'icon_size': '3x',
    },
}
