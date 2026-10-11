#!/bin/sh
set -eu
if [ ! -f /srv/bds/bedrock_server ]; then cp -a /opt/bds/. /srv/bds/; fi
cd /srv/bds
if [ ! -p poc-console ]; then mkfifo poc-console; fi
# Keep both FIFO ends open so a controller disconnect cannot close BDS stdin.
exec 3<>poc-console
exec ./bedrock_server <&3
