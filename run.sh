# !/bin/sh

# cd to your workspace
# created some folders for volumes
mkdir .redis
cd .redis

for group in group_01 group_02 group_03 group_04 group_05 group_06 group_other
do
    mkdir $group
    cd $group
    mkdir data
    echo "# bind 127.0.0.1" >> redis.conf
    echo "protected-mode no" >> redis.conf
    echo "appendonly yes" >> redis.conf
    cd ..
done

cd ..


docker-compose down
docker-compose up -d