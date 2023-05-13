#!/bin/bash

set -e

if [[ $# -ne 2 ]]; then
        echo "Usage: $0 <branch> <port>"
        exit 1
fi

cd /etc/nginx/

BRANCH=$1
PORT=$2

sed -e "s/<BRANCH_NAME>/$BRANCH/g" -e "s/<PORT>/$PORT/g" sites-available/dev-template.conf > sites-available/dev-${BRANCH}.conf
ln -f -s ../sites-available/dev-${BRANCH}.conf sites-enabled/dev-${BRANCH}.conf