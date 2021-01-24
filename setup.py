# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('VERSION.txt', 'r') as f:
    pkg_version = f.read().strip()


def get_long_description():
    with open('README.rst', 'r') as f:
        return f.read()


install_requires = [
    'beautifulsoup4 >= 4.1.1',
    'django >= 2.1,<3.2',
    'django-contrib-comments',
    'django-tinymce',
    'django-uuslug',
    'html2text',
    'odfpy >= 0.9.6',
    'python-bugzilla',
    'xmltodict',
    'kobo'
]

extras_require = {
    'mysql': ['mysqlclient >= 1.2.3'],
    'pgsql': ['psycopg2-binary == 2.8.5'],

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
        'pytest',
        'pytest-cov',
        'pytest-django',
        'sqlparse',
        'tox',
        'tox-docker==1.7.0'
    ],

    # Contain tools that assists the development
    'devtools': [
        'django-debug-toolbar',
        'tox',
        'django-extensions',
        'pygraphviz',
    ],

    # Required packages required to run async tasks
    'async': [
        'celery == 5.0.5',
    ],

    'multiauth': [
        'social-auth-app-django == 3.1.0',
    ]
}

setup(
    name='nitrate-tcms',
    version=pkg_version,
    description='A full-featured Test Case Management System',
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
        'Framework :: Django :: 2.2',
        'Framework :: Django :: 3.0',
        'Framework :: Django :: 3.1',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
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
