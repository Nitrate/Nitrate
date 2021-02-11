# Welcome to Nitrate

Nitrate is a new test plan, test run and test case management system, which is
written in Python and Django web framework.

Nitrate is installed and configured with minimized configuration to run.

Documentation: https://nitrate.readthedocs.io/

Source code: https://github.com/Nitrate/Nitrate/

Dockerfile: [docker/released/Dockerfile][]

## Usage

This image only has installed Nitrate Web application. The container running
from this image has to be linked with a MySQL or MariaDB container to work.

This image only has Nitrate Web application installed inside. For running a
complete functional Nitrate in your environment, there are several ways to run
and each of them requires a database instance.

### Run locally

Nitrate is able to run locally by either `docker` or `podman` and be linked to a
database container:

```
docker run --link nitrate_db:mariadb -p 80:80 -e NITRATE_DB_NAME=nitrate \
    quay.io/nitrate/nitrate:4.10
```

For launching the whole environment quickly and in an easier way than running
docker command directly, you can also use docker-compose to simplify the steps
and make the steps repeatable, and just:

```
docker-compose up
```

Nitrate source code provides a [docker-compose.yml][] already to up Nitrate
locally. Note that, please do not use it in any kind of production environment.

### Run in the cloud

To deploy Nitrate in the could, please refer to the documentation of the
specific cloud product.

In case you are using the OpenShift, please move to https://docs.openshift.com/.

In whatever the way you run the Nitrate, the environment variables and volumes
described following may be used to customize the use and maintenance.

## Environment Variables

### `NITRATE_DB_*`

There are a few of environment variables you can set to configure for the
database connection from container.

- `NITRATE_DB_ENGINE`: set to use which database backend. It could be `mysql` or
`pgsql`.

- `NITRATE_DB_NAME`: the database name to connect. This is optional. Default to
`nitrate`.

- `NITRATE_DB_USER`: the user name used to connect to database. This is optional.
Default to `nitrate`.

- `NITRATE_DB_PASSWORD`: the password used with username together to connect
database. This is optional. Without passing a password, empty password is
used to connect database. Hence, it depends on the authentication
configuration in database server side whether to allow login with empty
password.

- `NITRATE_DB_HOST`: the host name of database server. This is optional. Default
to connect to localhost. Generally, this variable must be set at least.

- `NITRATE_DB_PORT`: the database port to connect. This is optional. Default to
the database default port. Please consult the concrete database product
documentation. Generally, default port of MySQL and MariaDB is `3306`, and
PostgreSQL's is `5432`.

### `NITRATE_MIGRATE_DB`

This variable is optional and allow to run database migrations during launching
the container. This is useful particularly for the first time to run Nitrate.

### `NITRATE_SUPERUSER_USERNAME`, `NITRATE_SUPERUSER_PASSWORD`, `NITRATE_SUPERUSER_EMAIL`

These variables are optional to create a superuser account during launching the
container. All of these three variables must be set at the same time. This is
helpful for the first time to run Nitrate in order to login quickly just after
the container is launched successfully.

### `NITRATE_SET_DEFAULT_PERMS`

This variable is optional to create the default groups and grant permissions to
them.

## Volumes

### `/var/log/httpd`

The directory to store the httpd log files. Ensure the write permission is
granted properly.

### `/var/nitrate/uploads`

The directory to store the uploaded attachment files. Ensure the write
permission is granted properly.

### `/nitrate-config`

The directory holding the custom config module. Mount this volume when default
settings have to customized. For most of the cases running Nitrate in your cloud
environment, customization should be required. To customize the settings, create
a Python module `nitrate_custom_conf.py` inside a directory which will be
mounted to this container volume.

## Manual operations

Several environment variables mentioned above are optional to be set. Without
setting those variables, administrator is able to do the equivalent operations
manually.

### Run database migrations

```
docker exec [container name] django-admin migrate
```

### Create a superuser

```
docker exec [container name] django-admin createsuperuser
```

### Create default groups with permissions

```
docker exec [container name] django-admin setdefaultperms
```

## Report Issues

Report issue here https://github.com/Nitrate/Nitrate/issues/new

[docker/released/Dockerfile]: https://github.com/Nitrate/Nitrate/tree/develop/docker/released/Dockerfile
[docker-compose.yml]: https://github.com/Nitrate/Nitrate/blob/develop/docker-compose.yml