SPECFILE=python-nitrate-tcms.spec

default: help

DEFINE_OPTS=--define "_sourcedir $(PWD)/dist" --define "_srcrpmdir $(PWD)/dist" --define "_rpmdir $(PWD)/dist"


.PHONY: tarball
tarball:
	@python3 setup.py sdist


.PHONY: srpm
srpm:
	@rpmbuild $(DEFINE_OPTS) -bs $(SPECFILE)


.PHONY: rpm
rpm: srpm
	@rpmbuild $(DEFINE_OPTS) -ba $(SPECFILE)


.PHONY: flake8
flake8:
	@tox -e flake8


.PHONY: publish-to-pypi
publish-to-pypi: tarball
	@twine upload dist/nitrate-tcms-$(RELEASE_VERSION).tar.gz


CONTAINER ?= podman
RELEASE_VERSION ?= latest
DOCKER_ORG ?= quay.io/nitrate
IMAGE_TAG = $(DOCKER_ORG)/nitrate:$(RELEASE_VERSION)

.PHONY: release-image
release-image:
	@$(CONTAINER) build -t $(IMAGE_TAG) \
		-f ./docker/released/Dockerfile \
		--build-arg version=$(RELEASE_VERSION) .

.PHONY: dev-image
dev-image:
	@$(CONTAINER) build -t $(IMAGE_TAG:$(RELEASE_VERSION)=dev) \
		-f ./docker/dev/Dockerfile .

.PHONY: login-registry
login-registry:
	@if [ -n "$(QUAY_USER)" ] && [ -n "$(QUAY_PASSWORD)" ]; then \
		echo "$(QUAY_PASSWORD)" | $(CONTAINER) login \
			-u "$(QUAY_USER)" --password-stdin quay.io; \
	else \
		$(CONTAINER) login quay.io; \
	fi

.PHONY: publish-release-image
publish-release-image: login-registry
	$(CONTAINER) push $(IMAGE_TAG)

# By default, released image is pulled from remote registry.
# For the purpose of testing released image locally, execute target
# `release-image' manually before this up.
up-release-container: export IMAGE_VERSION = $(RELEASE_VERSION)
up-release-container:
	@docker-compose -f docker-compose.yml up

clear-release-container:
	@docker-compose -f docker-compose.yml rm

# Depends on dev-image
up-dev-container:
	@docker-compose -f docker-compose-dev.yml up

clear-dev-container:
	@docker-compose -f docker-compose-dev.yml rm

web-container-initconfig:
	# Make sure web is up from docker-compose.yml already
	# Database migrations
	@$(CONTAINER) exec -i -t --env DJANGO_SETTINGS_MODULE=tcms.settings.product nitrate_web_1 \
		/prodenv/bin/django-admin migrate
	# Create superuser admin
	@$(CONTAINER) exec -i -t --env DJANGO_SETTINGS_MODULE=tcms.settings.product nitrate_web_1 \
		/prodenv/bin/django-admin createsuperuser --username admin --email admin@example.com
	# Set permissions to default groups
	@$(CONTAINER) exec -i -t --env DJANGO_SETTINGS_MODULE=tcms.settings.product nitrate_web_1 \
		/prodenv/bin/django-admin setdefaultperms

ifeq ($(strip $(DB)),)
DB_ENVS=
else ifeq ($(strip $(DB)), sqlite)
DB_ENVS=
else ifeq ($(strip $(DB)), mysql)
DB_ENVS=NITRATE_DB_ENGINE=mysql NITRATE_DB_NAME=nitrate
else ifeq ($(strip $(DB)), pgsql)
DB_ENVS=NITRATE_DB_ENGINE=pgsql NITRATE_DB_NAME=nitrate NITRATE_DB_USER=postgres
else
$(error Unknown DB engine $(DB))
endif

MANAGE_PY=./src/manage.py

.PHONY: runserver
runserver:
	@if [ "$(DB)" == "mysql" ]; then \
		mysql -uroot -e "CREATE DATABASE IF NOT EXISTS nitrate CHARACTER SET utf8mb4;"; \
	elif [ "$(DB)" == "pgsql" ]; then \
		psql -U postgres -c "CREATE DATABASE nitrate" || :; \
	fi
	@$(DB_ENVS) $(MANAGE_PY) runserver

%:
	@# help: Match arbitrary manage.py commands.
	@$(DB_ENVS) $(MANAGE_PY) $@ $(args)


.PHONY: db_envs
db_envs:
	@# help: Print environment variables for a specific database engine set by DB.
	@for env in $(DB_ENVS); do \
    	echo "export $$env"; \
    done


.PHONY: help
help:
	@echo "Available targets:"
	@echo
	@grep --color=never "^.\+:$$" Makefile
