#!/bin/bash

set -e

if [[ $# -ne 1 ]]; then
        echo "Usage: $0 <org> <repo> <branch>"
        exit 1
fi

cd /etc/nginx/

ORG=$1
REPO=$2
BRANCH=$3

# Delete Config files if exits
sudo rm -f sites-enabled/dev-${ORG}-${REPO}-${BRANCH}.conf
sudo rm -f sites-available/dev-${ORG}-${REPO}-${BRANCH}.conf

