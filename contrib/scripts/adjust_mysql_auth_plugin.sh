set -ex
username=$1
password=$2
image=$3
c_name=$(docker ps -a --format '{{.Image}} {{.Names}}' | grep "${image}" | cut -d' ' -f2)
docker exec $c_name /bin/bash -c "
mysql -u${username} -p${password} \
-e \"ALTER USER '${username}'@'%' IDENTIFIED WITH mysql_native_password BY '${password}'\"
"
