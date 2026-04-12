# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup

- Create a virtual environment: `python3 -m venv .venv`
- Activate it: `source .venv/bin/activate`
- Install dependencies: `pip install -e .[devtools,tests]` (or use `requirements-devel.txt`)

### Django Management Commands

The Django management script is at `src/manage.py`. By default it uses `tcms.settings.devel`. Run from the project root:

- `./src/manage.py makemigrations` – create new migrations
- `./src/manage.py migrate` – apply migrations
- `./src/manage.py createsuperuser` – create admin user
- `./src/manage.py shell` – Django shell

### Building Requirements Files

The project uses `pip-compile` to generate pinned requirement files. Use the Makefile:

- `make requirements-devel.txt` – generates development requirements
- `make requirements-all.txt` – generates all optional dependencies
- `make requirements-basic.txt` – generates basic runtime dependencies
- `make requirements` – generates all three files

### Running Tests

**Primary test runner**: `tox` (runs across Python 3.10–3.13, Django 4.2, multiple databases)

- `tox` – run all environments (can be slow)
- `tox -e py313-django420-sqlite` – run tests with SQLite (fastest)
- `tox -e flake8` – lint Python code
- `tox -e black` – format Python code with black
- `tox -e isort` – check import sorting
- `tox -e bandit` – security linting
- `tox -e mypy-django420` – static type checking
- `tox -e jslint` – lint JavaScript files (requires npm install)
- `tox -e templatelint` – lint Django templates
- `tox -e doc8` – lint documentation
- `tox -e docs` – build documentation

**Running pytest directly** (faster iteration):

- `pytest tests/` – run all tests
- `pytest tests/path/to/test_file.py` – run specific test file
- `pytest tests/path/to/test_file.py::TestClass::test_method` – run single test
- Use `--cov` to see coverage: `pytest --cov=src/tcms/`

**Database-specific tests** (require containerized databases):

- Start test database: `make start-testdb-mysql` (or `start-testdb-mariadb`, `start-testdb-postgres`)
- Run tests: `tox -e py313-django420-mysql` (or `py313-django420-mariadb`, `py313-django420-postgres`)
- Stop database: `make stop-testdb-mysql` (or `stop-testdb-mariadb`, `stop-testdb-postgres`)

### Code Formatting

- `make format-code` – formats Python code with black (line length 100)
- `tox -e black` – also formats code
- `tox -e isort` – checks import ordering (use `--diff` to see changes)

### Development Server

- Set database engine: `export DB=sqlite` (or `mysql`, `pgsql`)
- `make db_envs` – prints the environment variables needed for the selected DB
- Run: `make runserver`
- For MySQL/PostgreSQL, ensure the database is running and accessible.

### Containerized Deployment

- `podman-compose -f container-compose.yml up` – runs Nitrate with MariaDB, RabbitMQ, web and worker containers
- Images are built from `quay.io/nitrate/web` and `quay.io/nitrate/worker`

### Building Packages

- `make sdist` – builds source distribution package
- `python3 -m build --sdist` – alternative

## Architecture Overview

Nitrate is a Django-based Test Case Management System (TCMS) with a modular architecture.

### Core Modules

- **`tcms.core`** – base models (`TCMSActionModel`, `TCMSContentTypeBaseModel`), utilities, and mixins
- **`tcms.testcases`** – TestCase, TestCaseText, TestCaseStatus, TestCaseCategory, and related linking tables
- **`tcms.testplans`** – TestPlan, TestPlanType, and plan‑case relationships
- **`tcms.testruns`** – TestRun, TestCaseRun (execution of a case in a run), TestRunStatus
- **`tcms.management`** – Product, Component, Version, Build, Priority, TestTag, etc.
- **`tcms.auth`** – authentication backends (Bugzilla, Kerberos, social‑auth)
- **`tcms.issuetracker`** – issue tracker integration (Bugzilla, JIRA, etc.)
- **`tcms.xmlrpc`** – XML‑RPC API (legacy compatibility)
- **`tcms.report`** – reporting functionality
- **`tcms.profiles`** – user profiles and preferences
- **`tcms.search`** – search backends

### Key Design Patterns

- **TCMSActionModel** – provides automatic logging of who created/changed a record and when.
- **TCMSContentTypeBaseModel** – generic foreign‑key base for flexible relationships.
- **Signals** – used for email notifications, cache invalidation, and plugin hooks.
- **Plugin system** – `tcms.plugins_support` allows external modules to register models and signals.

### Database

- Supports SQLite (development), MySQL/MariaDB, and PostgreSQL.
- Migrations are Django‑managed.
- Test environments can spin up containerized databases via Make targets.

### Frontend

- Django templates with Bootstrap.
- Custom JavaScript modules in `src/static/js/` (e.g., `nitrate.core.js`, `nitrate.testplans.js`).
- ESLint checks are part of the CI (`tox -e jslint`).

### Asynchronous Tasks

- Optional Celery integration (`async` extra).
- Worker image (`quay.io/nitrate/worker`) handles background jobs.

### Settings

- Base configuration: `src/tcms/settings/common.py`
- Development overrides: `src/tcms/settings/devel.py`
- Test settings: `src/tcms/settings/test.py`
- Production‑like settings: `src/tcms/settings/product.py`
- Environment variables (see `common.py` for details) control database, secret key, etc.

### Testing Strategy

- Unit tests in `tests/` mirror the `src/tcms/` structure.
- Uses `pytest‑django` and `factory_boy`.
- Coverage reports generated via `pytest‑cov`.
- Linting and static analysis are part of the tox matrix.

## Workflow Tips

- **Running a single test**: `pytest tests/testcases/test_views.py -xvs`
- **Debugging with Django toolbar**: install `django-debug-toolbar` (included in `devtools` extra) and enable in `devel.py`.
- **Checking migrations**: `./src/manage.py makemigrations` (run from project root with appropriate `DJANGO_SETTINGS_MODULE`).
- **Accessing the XML‑RPC API**: endpoints are under `/xmlrpc/`; see `src/tcms/xmlrpc/api/` for implementations.
- **Adding a new optional dependency**: add to `pyproject.toml` under `[project.optional‑dependencies]`, then regenerate requirement files with `make requirements‑all.txt`.

## Important Files

- `pyproject.toml` – project metadata, dependencies, tool configurations (black, isort, mypy, pytest, coverage, bandit)
- `tox.ini` – multi‑environment test matrix and linting commands
- `Makefile` – common development tasks
- `container‑compose.yml` – Podman‑based multi‑container setup
- `src/manage.py` – Django management script
- `VERSION.txt` – single‑source version number