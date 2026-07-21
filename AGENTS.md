# AGENTS.md

## Project Overview

Nitrate is a full-featured Test Case Management System written in Python and Django. It manages test plans, test cases, and test runs with features including:

- Multiple authentication backends (Bugzilla, Kerberos, social auth)
- Fast search for plans, cases, and runs
- Powerful access control
- XMLRPC APIs
- Extensible issue tracker integration
- Celery-based asynchronous task support

**Tech Stack:** Python 3.10–3.13, Django 4.2, MySQL/MariaDB/PostgreSQL

**License:** GPLv2+

## Project Structure

```
src/                   # Application source code
  tcms/                # Main Django app package
    core/              # Core module: models, views, forms, templatetags, management commands
    testcases/         # Test case management
    testplans/         # Test plan management
    testruns/          # Test run management
    auth/              # Authentication backends (Kerberos, Bugzilla)
    issuetracker/      # Issue tracker integration
    xmlrpc/            # XMLRPC API layer
    comments/          # Comment system (django-contrib-comments)
    linkreference/     # Link references between objects
    logs/              # Activity logging
    management/        # Django management commands
    profiles/          # User profiles
    report/            # Reporting module
    search/            # Search functionality
    settings/          # Django settings (devel, test, production)
    integration/       # Integration utilities
    plugins_support/   # Plugin support framework
  static/              # Static files (CSS, JS, images)
  templates/           # Django templates
  locale/              # Internationalization files
  manage.py            # Django management script

tests/                 # Test suite
  conftest.py          # Pytest fixtures and configuration
  factories.py         # Test factories (factory_boy)
  testcases/           # Tests for test cases
  testplans/           # Tests for test plans
  testruns/            # Tests for test runs
  xmlrpc/              # Tests for XMLRPC API
  core/                # Tests for core module
  data/                # Test data files
  js/                  # JavaScript tests

docs/                  # Documentation (Sphinx, reStructuredText)
contrib/               # Contributed scripts and configurations
```

## Development Commands

### Setup

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[async,bugzilla,krbauth,mysql,pgsql,tests,devtools,docs]"
```

### Running the development server

```bash
make runserver              # SQLite (default)
make runserver DB=mysql     # MySQL
make runserver DB=pgsql     # PostgreSQL
```

### Code Quality

```bash
tox -e flake8          # Python linting
tox -e black           # Python formatting check
tox -e isort           # Import order check
tox -e bandit          # Security linting
tox -e mypy-django420  # Type checking
tox -e jslint          # JavaScript linting
tox -e templatelint    # Django template linting
tox -e docs            # Documentation build
tox -e doc8            # Documentation linting
```

### Dependency Management

Dependencies are managed with `uv`.

To upgrade a dependency, edit `pyproject.toml`.

Lock dependencies, run `uv lock`.

### Building

```bash
make sdist                     # Build source distribution (python3 -m build --sdist)
```

### Test Databases (Podman containers)

```bash
make start-testdb-mariadb      # Start MariaDB 10.11.8 on port 33061
make start-testdb-mysql        # Start MySQL 8.0.22 on port 33062
make start-testdb-postgres     # Start PostgreSQL 16.3 on port 54321
make check-testdb-health db_engine=mariadb   # Verify test DB is healthy

make stop-testdb-mariadb       # Stop containers
make stop-testdb-mysql
make stop-testdb-postgres
```

### Running Containers (Quick Start)

```bash
podman-compose -f container-compose.yml up
```

## Testing

### Running tests

```bash
# All tests with default SQLite
tox

# Specific Python/Django combination
tox -e py313-django420-sqlite

# With real databases (start containers first)
tox -e py313-django420-mysql
tox -e py313-django420-mariadb
tox -e py313-django420-postgres

# Run pytest directly
python3 -m pytest tests/

# Run specific test file
python3 -m pytest tests/testcases/test_views.py

# Run tests with coverage
python3 -m pytest --cov=src/tcms/ tests/
```

### Test Configuration

- Django settings module: `tcms.settings.test`
- Test runner: `pytest-django`
- Test database environments configured via tox `NITRATE_DB_*` variables
- Test factories use `factory_boy`
- Coverage: excludes `migrations/`, `settings/`, `urls.py`, `wsgi.py`

## Code Style

- **Line length:** 100 characters (Python), `black` and `isort` configured
- **Formatter:** `black` with `--line-length 100`
- **Import sorting:** `isort` with `black` profile; `migrations` directory excluded
- **Quotes:** As formatted by `black`
- **Type checking:** `mypy` with `django-stubs` plugin
- **JS linting:** `eslint` configured via `eslint.config.js`
- **Naming:** Django conventions — models in `models.py` (or `models/` package), views in `views.py` (or `views/` package)

## Key Django Apps

| App | Purpose |
|-----|---------|
| `tcms.core` | Shared models, views, forms, middlewares, templatetags |
| `tcms.testcases` | Test case CRUD, categorization, components |
| `tcms.testplans` | Test plan management and organization |
| `tcms.testruns` | Test execution tracking and results |
| `tcms.xmlrpc` | XMLRPC API for external integrations |
| `tcms.issuetracker` | External issue tracker integration |
| `tcms.auth` | Authentication backends (Kerberos, Bugzilla) |

## Settings Modules

- `tcms.settings.devel` — Development settings
- `tcms.settings.test` — Test settings
- Production settings configured via environment variables (see container-compose.yml)

## Container Images

Three pre-built images on quay.io:
- `quay.io/nitrate/web` — Web application
- `quay.io/nitrate/worker` — Celery worker
- `quay.io/nitrate/base` — Base image for custom builds

## CI/CD

CI runs on GitHub Actions (see `.github/workflows/`). Primary workflow: `unittests.yaml`.
