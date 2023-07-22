
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
