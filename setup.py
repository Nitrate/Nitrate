from setuptools import setup, find_packages


def read_file(filename: str) -> str:
    with open(filename, "r", encoding="utf-8") as f:
        return f.read().strip()


setup(
    name="nitrate-tcms",
    version=read_file("VERSION.txt"),
    description="A full-featured Test Case Management System",
    long_description=read_file("README.rst"),
    author="Nitrate Team",
    maintainer="Chenxiong Qi",
    maintainer_email="qcxhome@gmail.com",
    url="https://github.com/Nitrate/Nitrate/",
    license="GPLv2+",
    keywords="test case plan run",
    platforms=["any"],
    install_requires=[
        "beautifulsoup4==4.11.1",
        "django>=3.2,<4",
        "django-contrib-comments==2.2.0",
        "django-tinymce==3.5.0",
        "django-uuslug==2.0.0",
        "html2text==2020.1.16",
        "kobo==0.25.0",
        "odfpy==1.4.1",
        "xmltodict==0.13.0",
    ],
    extras_require={
        'mysql': ['mysqlclient==2.1.1'],
        'pgsql': ['psycopg2-binary==2.9.5'],
        'socialauth': ['social-auth-app-django==5.5.0'],

        # Required packages required to run async tasks
        'async': ['celery==5.2.6'],

        # Used for authentication backend based on bugzilla and the asynchronous
        # task adding using bugzilla.
        'bugzilla': ['python-bugzilla==3.2.0'],

        # Required for tcms.auth.backends.KerberosBackend
        'krbauth': ['kerberos==1.3.0'],

        # Packages for building documentation
        'docs': [
            'Sphinx >= 1.1.2',
            'sphinx_rtd_theme',
        ],

        # Necessary packages for running tests
        'tests': [
            "beautifulsoup4==4.11.1",
            "coverage[toml]",
            "factory_boy",
            "flake8",
            "pytest",
            "pytest-cov",
            "pytest-django",
            "sqlparse",
            "tox",
            "tox-docker>=2.0.0",
        ],

        # Contain tools that assists the development
        'devtools': [
            "black",
            'django-debug-toolbar',
            'django-stubs',
            'tox',
        ],
    },
    python_requires='>=3.9',
    package_dir={'': 'src'},
    packages=find_packages('src', exclude=['test*']),
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Framework :: Django",
        "Framework :: Django :: 3.2",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
    ],
    project_urls={
        "Issue Tracker": "https://github.com/Nitrate/Nitrate/issues",
        "Source Code": "https://github.com/Nitrate/Nitrate",
        "Documentation": "https://nitrate.readthedocs.io/",
        "Release Notes": "https://nitrate.readthedocs.io/en/latest/releases/",
        "Container Images": "https://quay.io/organization/nitrate",
    },
)
