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
IMAGE = $(DOCKER_ORG)/nitrate:$(RELEASE_VERSION)
WORKER_IMAGE = $(DOCKER_ORG)/nitrate-worker:$(RELEASE_VERSION)

ifeq ($(RELEASE_VERSION),latest)
BUILD_LATEST=yes
else
BUILD_LATEST=no
endif

.PHONY: image
image:
	@cd container && $(CONTAINER) build -t $(IMAGE) \
		-f Containerfile \
		--build-arg version=$(RELEASE_VERSION) \
		--build-arg build_latest=$(BUILD_LATEST) .

.PHONY: worker-image
worker-image:
	@cd container && $(CONTAINER) build -t $(WORKER_IMAGE) \
		-f Containerfile-worker \
		--build-arg version=$(RELEASE_VERSION) \
		--build-arg build_latest=$(BUILD_LATEST) .

.PHONY: login-registry
login-registry:
	@if [ -n "$(QUAY_USER)" ] && [ -n "$(QUAY_PASSWORD)" ]; then \
		echo "$(QUAY_PASSWORD)" | $(CONTAINER) login \
			-u "$(QUAY_USER)" --password-stdin quay.io; \
	else \
		$(CONTAINER) login quay.io; \
	fi

.PHONY: publish-images
publish-images: login-registry
	$(CONTAINER) push $(IMAGE)
	$(CONTAINER) push $(WORKER_IMAGE)

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


mock_root ?= fedora-33-x86_64
rpm_dist = $(shell echo "$(mock_root)" | cut -d'-' -f2)
local_build_deps=https://download.copr.fedorainfracloud.org/results/cqi/python-nitrate-tcms/$(mock_root)/01874726-python-django-tinymce/python3-django-tinymce-3.2.0-1.fc$(rpm_dist).noarch.rpm
nvr=$(shell rpm -q --qf "%{nvr}\n" --specfile python-nitrate-tcms.spec | grep python-nitrate-tcms)
mock=mock --root $(mock_root)

.PHONY: quick-local-build
quick-local-build:
	@make tarball srpm
	@$(mock) --init
	@$(mock) --install $(local_build_deps)
	@$(mock) --no-clean --rebuild dist/$(nvr).src.rpm


.PHONY: format-code
format-code:
	@black --line-length $(shell grep "^max_line_length" tox.ini | cut -d' '  -f3) src/tcms src/tests


.PHONY: help
help:
	@echo "Available targets:"
	@echo
	@grep --color=never "^.\+:$$" Makefile
