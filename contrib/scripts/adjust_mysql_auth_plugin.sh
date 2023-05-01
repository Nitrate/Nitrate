set -ex
username=$1
password=$2
tempfile=$(mktemp)

# Guess container name of the test database
if ! docker ps -a --format "{{ json .Names }}" | tr -d '"' | grep "^testdb_mysql" >"$tempfile" 2>&1; then
	echo "error: cannot find container testdb_mysql"
	exit 1
fi
c_name=$(cat "$tempfile")

docker exec "$c_name" /bin/bash -c "
mysql -u${username} -p${password} \
-e \"ALTER USER '${username}'@'%' IDENTIFIED WITH mysql_native_password BY '${password}'\"
"
