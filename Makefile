SPECFILE=nitrate.spec

default: help

DIST_DIR=$(shell pwd)/dist/
DEFINE_OPTS=--define "_sourcedir $(PWD)/dist" --define "_srcrpmdir $(PWD)/dist" --define "_rpmdir $(PWD)/dist"


.PHONY: tarball
tarball:
	@python setup.py sdist


.PHONY: srpm
srpm: tarball
	@rpmbuild $(DEFINE_OPTS) -bs $(SPECFILE)


.PHONY: rpm
rpm: srpm
	@rpmbuild $(DEFINE_OPTS) -ba $(SPECFILE)


.PHONY: build
build:
	python setup.py build


.PHONY: install
install:
	python setup.py install


.PHONY: flake8
flake8:
	@tox -e flake8


.PHONY: check
check:
	@tox


.PHONY: tags
tags:
	@rm -f .tags
	@ctags -R --languages=Python,Javascript --python-kinds=-im \
		--exclude=build --exclude=tcms/static/js/lib --exclude=dist --exclude=.tox -f .tags


.PHONY: etags
etags:
	@rm -f TAGS
	@ctags -R -e --languages=Python,Javascript --python-kinds=-im \
		--exclude=build --exclude=tcms/static/js/lib --exclude=dist --exclude=.tox -f TAGS

ifeq ($(DOCKER_ORG),)
  DOCKER_ORG='nitrate'
endif

NITRATE_VERSION=$(shell cat VERSION.txt | tr -d '\n')

release-image:
	@docker build \
		-t $(DOCKER_ORG)/nitrate:$(NITRATE_VERSION) \
		-f ./docker/released/Dockerfile \
		--build-arg VERSION=$(NITRATE_VERSION) .

dev-image:
	@docker build -t nitrate:dev -f Dockerfile-dev .

# ./manage.py runserver with default SQLite database
runserver:
	@./src/manage.py runserver

runserver-mysql:
	@mysql -uroot -e "CREATE DATABASE IF NOT EXISTS nitrate CHARACTER SET utf8mb4;"
	@NITRATE_DB_ENGINE=mysql NITRATE_DB_NAME=nitrate ./src/manage.py runserver

runserver-pgsql:
	@echo "CREATE DATABASE nitrate" | psql -U postgres || true
	@NITRATE_DB_ENGINE=pgsql NITRATE_DB_NAME=nitrate NITRATE_DB_USER=postgres ./src/manage.py runserver

.PHONY: help
help:
	@echo 'Usage: make [command]'
	@echo ''
	@echo 'Available commands:'
	@echo ''
	@echo '  rpm              - Create RPM'
	@echo '  srpm             - Create SRPM'
	@echo '  tarball          - Create tarball. Run command: python setup.py sdist'
	@echo '  flake8           - Check Python code style throughout whole source code tree'
	@echo '  test             - Run all tests default'
	@echo '  build            - Run command: python setup.py build'
	@echo '  install          - Run command: python setup.py install'
	@echo '  tags             - Refresh tags for VIM. Default filename is .tags'
	@echo '  etags            - Refresh tags for Emacs. Default filename is TAGS'
	@echo '  help             - Show this help message and exit. Default if no command is given'
