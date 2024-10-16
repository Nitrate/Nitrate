
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

ifeq ($(strip $(detach)),yes)
detach_opt=-d
else
detach_opt=
endif

db_engine ?=
common_health_options = --health-interval=5s --health-timeout=2s --health-retries=3

mariadb_image = mariadb:10.11.8@sha256:75f6e61397758489d1dccf95db33b6b49ebfc7ec1253d40060fdf8ceb7f938a3
mysql_image = mysql:8.4.3@sha256:0fd2898dc1c946b34dceaccc3b80d38b1049285c1dab70df7480de62265d6213
postgres_image = postgres:16.3@sha256:0aafd2ae7e6c391f39fb6b7621632d79f54068faebc726caf469e87bd1d301c0

# MariaDB setup for testenv

.PHONY: start-testdb-mariadb
start-testdb-mariadb:
	podman run --rm $(detach_opt) \
		--name=testdb-mariadb \
		-p 33061:3306 \
		-e MYSQL_ROOT_PASSWORD=pass \
		--health-cmd="mysqladmin ping -uroot -ppass" \
		$(common_health_options) \
		$(mariadb_image)

.PHONY: stop-testdb-mariadb
stop-testdb-mariadb:
	podman stop testdb-mariadb || :

# MySQL setup for testenv

.PHONY: start-testdb-mysql
start-testdb-mysql:
	podman run --rm $(detach_opt) \
		--name=testdb-mysql \
		-p 33062:3306 \
		-e MYSQL_ROOT_PASSWORD=pass \
		--health-cmd="mysqladmin ping -uroot -ppass" \
		$(common_health_options) \
		$(mysql_image)

.PHONY: stop-testdb-mysql
stop-testdb-mysql:
	podman stop testdb-mysql || :

# PostgreSQL setup for testenv

.PHONY: start-testdb-postgres
start-testdb-postgres:
	podman run --rm $(detach_opt) \
		--name=testdb-postgres \
		-p 54321:5432 \
		-e POSTGRES_PASSWORD=pass \
		--health-cmd="PGPASSWORD=pass psql -h 127.0.0.1 -U postgres -c 'SELECT 1'" \
		$(common_health_options) \
		$(postgres_image)

.PHONY: stop-testdb-postgres
stop-testdb-postgres:
	podman stop testdb-postgres || :

.PHONY: check-testdb-health
check-testdb-health:
	@for i in $$(seq 1 5); do \
	  health_status=$$(podman inspect testdb-$(db_engine) | jq -r '.[].State.Health.Status'); \
	  [ "x$$health_status" = "xhealthy" ] && break; \
	  if [ $$i -eq 5 ]; then \
		echo "testdb $(db_engine) container is not healthy. Seems failed to start." >&2; \
		echo "container inspect:" >&2; \
		podman inspect testdb-$(db_engine) | jq '.[].State' >&2; \
		exit 1; \
	  else \
		echo "Sleep 2s then have another health check" >&2; \
		sleep 2s; \
	  fi; \
	  done; \
	  echo "Test database $(db_engine) is healthy."
