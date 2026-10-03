#!/bin/sh
set -eu
mkdir -p /data
chown vetra:vetra /data
exec gosu vetra "$@"
