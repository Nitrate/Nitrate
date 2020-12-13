# Welcome to use Nitrate

Nitrate is a new test plan, test run and test case management system, which is
written in Python and Django web framework.

Nitrate is installed and configured with minimized configuration to run.

Documentation: [https://nitrate.readthedocs.io/](https://nitrate.readthedocs.io/)

Source code: [https://github.com/Nitrate/Nitrate/](https://github.com/Nitrate/Nitrate/)

Dockerfile: [docker/released/Dockerfile](https://github.com/Nitrate/Nitrate/tree/develop/docker/released/Dockerfile)

## Usage

### How to Run

This image only has installed Nitrate Web application. The container running
from this image has to be linked with a MySQL or MariaDB container to work.

For example to run Nitrate with a MariaDB:

```
docker run --link nitrate_db:mariadb -p 80:80 -e NITRATE_DB_NAME=nitrate \
    quay.io/nitrate/nitrate:4.9
```

### Before Use

Before logging into Nitrate, you may need to complete following tasks:

- run database migrations if run Nitrate for the first time or there are
  migrations included in a release.

  ```
  docker exec -i -t --env DJANGO_SETTINGS_MODULE=tcms.settings.product \
      container_name /prodenv/bin/django-admin migrate
  ```

- create initial users in database manually. This initial user is usually a
  superuser os that someone can log into Nitrate with this account to manage
  service.

  ```
  docker exec -i -t --env DJANGO_SETTINGS_MODULE=tcms.settings.product \
      container_name /prodenv/bin/django-admin createsuperuser \
      --username admin --email address
  ```

- Set permissions to default groups. This is optional, but nice-to-have.

  ```
  docker exec -i -t --env DJANGO_SETTINGS_MODULE=tcms.settings.product \
      container_name /prodenv/bin/django-admin setdefaultperms
  ```

## Environment Variables

There are a few of environment variables you can set to configure container.

- `NITRATE_DB_ENGINE`: set to use which database backend. It could be `mysql`
  or `pgsql`.
- `NITRATE_DB_NAME`: the database name to connect. This is optional. Default to
  `nitrate`.
- `NITRATE_DB_USER`: the user name used to connect to database. This is
  optional. Default to `nitrate`.
- `NITRATE_DB_PASSWORD`: the password used with username together to connect
  database. This is optional. Without passing a password, empty password is
  used to connect database. Hence, it depends on the authentication
  configuration in database server side whether to allow login with empty
  password.
- `NITRATE_DB_HOST`: the host name of database server. This is optional.
  Default to connect to localhost. Generally, this variable must be set at
  least.
- `NITRATE_DB_PORT`: the database port to connect. This is optional. Default
  to the database default port. Please consult the concrete database product
  documentation. Generally, default port of MySQL and MariaDB is `3306`, and
  PostgreSQL's is `5432`.

## Report Issues

Report issue here [https://github.com/Nitrate/Nitrate/issues/new](https://github.com/Nitrate/Nitrate/issues/new)
