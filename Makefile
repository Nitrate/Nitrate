
.PHONY: sdist
sdist:		# Build source distribution package.
	@python3 -m build --sdist

ifeq ($(strip $(DB)),)
DB_ENVS=
else ifeq ($(strip $(DB)), sqlite)
DB_ENVS=
else ifeq ($(strip $(DB)), mysql)
DB_ENVS=NITRATE_DB_ENGINE=mysql NITRATE_DB_NAME=nitrate
else ifeq ($(strip $(DB)), pgsql)
DB_ENVS=NITRATE_DB_ENGINE=pgsql NITRATE_DB_NAME=nitrate NITRATE_DB_USER=postgres
else
$(error Unknown DB engine $(DB). Available choices are sqlite, mysql, pgsql)
endif

MANAGE_PY=./src/manage.py

.PHONY: runserver
runserver:		# Run local Django development server.
	@if [ "$(DB)" == "mysql" ]; then \
		mysql -uroot -e "CREATE DATABASE IF NOT EXISTS nitrate CHARACTER SET utf8mb4;"; \
	elif [ "$(DB)" == "pgsql" ]; then \
		psql -U postgres -c "CREATE DATABASE nitrate" || :; \
	fi
	$(DB_ENVS) $(MANAGE_PY) runserver $(args)


.PHONY: db_envs
db_envs:		# Print environment variables for a specific database engine set by DB.
	@for env in $(DB_ENVS); do \
    	echo "export $$env"; \
    done


.PHONY: format-code
format-code:		# Format Python code with black.
	@black --line-length $(shell grep "^max_line_length" tox.ini | cut -d' '  -f3) src/tcms tests

detach_testdb_container ?= false
gh_wf_unittests = .github/workflows/unittests.yaml
gh_wf_services = .jobs.unittests.services

# MariaDB setup for testenv

.PHONY: start-testdb-mariadb
start-testdb-mariadb:
	podman run --rm -p 33061:3306 -e MYSQL_ROOT_PASSWORD=pass \
		$(shell yq '$(gh_wf_services).mariadb.options' $(gh_wf_unittests)) \
		$(shell yq '$(gh_wf_services).mariadb.image' $(gh_wf_unittests))

.PHONY: stop-testdb-mariadb
stop-testdb-mariadb:
	podman stop testdb-mariadb || :

# MySQL setup for testenv

.PHONY: start-testdb-mysql
start-testdb-mysql:
	podman run --rm -p 33062:3306 -e MYSQL_ROOT_PASSWORD=pass \
		$(shell yq '$(gh_wf_services).mysql.options' $(gh_wf_unittests)) \
		$(shell yq '$(gh_wf_services).mysql.image' $(gh_wf_unittests))

.PHONY: stop-testdb-mysql
stop-testdb-mysql:
	podman stop testdb-mysql || :

# PostgreSQL setup for testenv

.PHONY: start-testdb-pgsql
start-testdb-pgsql:
	podman run --name testdb-pgsql --rm -p 54321:5432 \
		-e POSTGRES_PASSWORD=pass \
		$(shell yq '$(gh_wf_services).postgres.options' $(gh_wf_unittests)) \
		$(shell yq '$(gh_wf_services).postgres.image' $(gh_wf_unittests))

.PHONY: stop-testdb-pgsql
stop-testdb-pgsql:
	podman stop testdb-pgsql || :
