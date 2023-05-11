#!/bin/bash

set -e

if [[ $# -ne 1 ]]; then
        echo "Usage: $0 <branch>"
        exit 1
fi

cd /etc/nginx/

BRANCH=$1

# Delete Config files if exits
rm -f sites-enabled/dev-${BRANCH}.conf
rm -f sites-available/dev-${BRANCH}.conf

