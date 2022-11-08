# !/bin/sh

# remove tabot related containers
sudo docker rm -f $(sudo docker ps -aq --filter name=tabot)

# remove all images without at least one container associated to them
sudo docker image prune -a

# remove tabot related docker network
sudo docker network rm tabot