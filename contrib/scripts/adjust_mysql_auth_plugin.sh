set -ex
username=$1
password=$2
c_name=$3
docker exec $c_name /bin/bash -c "
mysql -u${username} -p${password} \
-e \"ALTER USER '${username}'@'%' IDENTIFIED WITH mysql_native_password BY '${password}'\"
"
