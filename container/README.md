# Welcome to Nitrate

Nitrate is a full-featured test plan, test run and test case management system,
which is written in Python and Django web framework.

Nitrate is installed and configured with minimized configuration to run.

Related Links:

- Documentation: https://nitrate.readthedocs.io/
- Source code: https://github.com/Nitrate/Nitrate/
- Containerfile for the Web container image: [container/Containerfile](https://github.com/Nitrate/Nitrate/blob/master/container/Containerfile)
- Containerfile for the worker container image: [container/Containerfile-worker](https://github.com/Nitrate/Nitrate/blob/master/container/Containerfile-worker)

## Tags

`latest` is applied to the image built from latest `develop` branch. It can also
be called the development version of Nitrate.

For a regular release, a specific version like `4.10` is applied to the image.

For all tags, please move to [Tags](https://quay.io/repository/nitrate/nitrate?tab=tags) page.

## Worker Image

Nitrate supports to schedule asynchronous tasks as Celery tasks. Hence, worker
container is required to receive the tasks from a broker and execute them. There
is a built worker image in the [nitrate-worker](https://quay.io/repository/nitrate/nitrate-worker?tab=tags)
repository. If you need the asynchronous functionality, the worker image could
be deployed with this Web image together in your environment.

The worker image has same tag scheme. Refer to the above [Tags](#tags) section.

When making a new release of Nitrate, both this Web and the worker image are
built and published to the repositories individually.

**Hint**: You can try the worker image with the [container-compose.yml](https://github.com/Nitrate/Nitrate/blob/master/container-compose.yml).

## Usage

This image only has installed Nitrate Web application. If persistent data
storage is required, a well-configured database container, like MariaDB or
PostgreSQL, has to be deployed as well.

In practice, there are several ways to run the container.

### Run locally

Nitrate is able to run locally by either `docker` or `podman` and be linked to a
database container:

```
podman run -p 80:80 -t quay.io/nitrate/nitrate:4.12
```

Following various environment variables can be set to initialize the container
to connect the database container.

To launch the whole environment quickly in an easier way than running podman
command, you can use the `podman-compose` or `docker-compose` to up containers.

```
podman-compose up
```

Nitrate source code provides the [container-compose.yml](https://github.com/Nitrate/Nitrate/blob/master/container-compose.yml)
to up Nitrate locally. **Note that**, please do not use it as a production
environment.

### Run in the cloud

To deploy Nitrate in the could, please refer to the documentation of the
specific cloud product.

In case you are using the OpenShift, please move to https://docs.openshift.com/.

In whatever the way you run the Nitrate in the cloud, the environment variables
and volumes described following may be used to customize the use and maintenance.

## Environment Variables

### `NITRATE_DB_*`

There are a few of environment variables you can set to configure for the
database connection from the Web container.

- `NITRATE_DB_ENGINE`: set to use which database backend. It could be `mysql` or
`pgsql`.

- `NITRATE_DB_NAME`: the database name to connect. This is optional. Default to
`nitrate`.

- `NITRATE_DB_USER`: the username used to connect to database. This is optional.
Default to `nitrate`.

- `NITRATE_DB_PASSWORD`: the password used with username together to connect
a database. This is optional. Without passing a password, empty password is
used to connect the database. Hence, it depends on the authentication
configuration in database server side whether to allow logging in with empty
password.

- `NITRATE_DB_HOST`: the host name of database server. This is optional. Default
to connect to localhost. Generally, this variable must be set at least.

- `NITRATE_DB_PORT`: the database port to connect. This is optional. Default to
the database default port. Please consult the concrete database product
documentation. Generally, default port of MySQL and MariaDB is `3306`, and
PostgreSQL's is `5432`.

### `NITRATE_MIGRATE_DB`

This variable is optional and allows to run the database migrations during
launching the container. This is useful particularly for the first time to run
Nitrate.

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
settings have to be customized. For most of the cases running Nitrate in your
cloud environment, customization should be required. To customize the settings,
create a Python module `nitrate_custom_conf.py` inside a directory which will be
mounted to this container volume.

## Manual operations

Several environment variables mentioned above are optional to be set. Without
setting those variables, administrator is able to do the equivalent operations
manually.

### Run database migrations

```
podman exec -it [container name] django-admin migrate
```

### Create a superuser

```
podman exec -it [container name] django-admin createsuperuser
```

### Create default groups with permissions

```
podman exec -it [container name] django-admin setdefaultperms
```

## Report Issues

Report issue here https://github.com/Nitrate/Nitrate/issues/new