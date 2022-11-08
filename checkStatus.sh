# !/bin/sh

sudo docker ps -as --filter name=tabot --format "table {{.Names}}\t{{.Status}}\t{{.Size}}\t{{.Ports}}" | sort | grep --color "tabot\|$"