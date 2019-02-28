# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('VERSION.txt', 'r') as f:
    pkg_version = f.read().strip()


def get_long_description():
    with open('README.rst', 'r') as f:
        return f.read()


install_requires = [
    'beautifulsoup4 >= 4.1.1',
    'django >= 1.11,<3.0',
    'django-contrib-comments == 1.8.0',
    'django-tinymce == 2.7.0',
    'django-uuslug == 1.1.8',
    'html2text',
    'odfpy >= 0.9.6',
    'python-bugzilla',
    'xmltodict',
    'kobo == 0.9.0'
]

extras_require = {
    'mysql': ['PyMySQL == 0.9.2'],
    'pgsql': ['psycopg2 == 2.7.5'],

    # Required for tcms.auth.backends.KerberosBackend
    'krbauth': [
        'kerberos == 1.2.5'
    ],

    # Packages for building documentation
    'docs': [
        'Sphinx >= 1.1.2',
        'sphinx_rtd_theme',
    ],

    # Necessary packages for running tests
    'tests': [
        'beautifulsoup4',
        'coverage',
        'factory_boy',
        'flake8',
        'mock',
        'pytest < 4.2.0',
        'pytest-cov',
        'pytest-django',
    ],

    # Contain tools that assists the development
    'devtools': [
        'django-debug-toolbar == 1.7',
        'tox',
        'django-extensions',
        'pygraphviz',
        'future-breakpoint',
    ],

    # Required packages required to run async tasks
    'async': [
        'celery == 4.2.0',
    ],

    'multiauth': [
        'social-auth-app-django == 3.1.0',
    ]
}

setup(
    name='Nitrate',
    version=pkg_version,
    description='Test Case Management System',
    long_description=get_long_description(),
    author='Nitrate Team',
    maintainer='Chenxiong Qi',
    maintainer_email='qcxhome@gmail.com',
    url='https://github.com/Nitrate/Nitrate/',
    license='GPLv2+',
    keywords='test case',
    install_requires=install_requires,
    extras_require=extras_require,
    python_requires='>=3.6',
    package_dir={'': 'src'},
    packages=find_packages('src', exclude=['test*']),
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Framework :: Django',
        'Framework :: Django :: 1.11',
        'Framework :: Django :: 2.0',
        'Framework :: Django :: 2.1',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Software Development :: Testing',
    ],
    project_urls={
        'Issue Tracker': 'https://github.com/Nitrate/Nitrate/issues',
        'Source Code': 'https://github.com/Nitrate/Nitrate',
        'Documentation': 'https://nitrate.readthedocs.io/',
    },
)
