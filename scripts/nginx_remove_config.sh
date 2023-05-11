#!/bin/bash

set -e

if [[ $# -ne 3 ]]; then
        echo "Usage: $0 <org> <repo> <branch>"
        exit 1
fi

cd /etc/nginx/

ORG=$1
REPO=$2
BRANCH=$3

# Delete Config files if exits
rm -f sites-enabled/dev-gen-${ORG}-${REPO}-${BRANCH}.conf
rm -f sites-available/dev-gen-${ORG}-${REPO}-${BRANCH}.conf

