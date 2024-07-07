set -ex

username=$1
password=$2

CONTAINER_NAME=testdb-mysql

if ! docker inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
    echo "error: cannot find container $CONTAINER_NAME" >&2
    exit 1
fi

ALTER_USER_CMD="ALTER USER '${username}'@'%' IDENTIFIED WITH mysql_native_password BY '${password}'"
docker exec "$CONTAINER_NAME" /bin/bash -c "mysql -u${username} -p${password} -e \"${ALTER_USER_CMD}\""
