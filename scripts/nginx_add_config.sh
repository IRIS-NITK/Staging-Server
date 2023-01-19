#!/bin/bash

set -e

if [[ $# -ne 4 ]]; then
        echo "Usage: $0 <org> <repo> <branch> <port>"
        exit 1
fi

cd /etc/nginx/

ORG=$1
REPO=$2
BRANCH=$3
PORT=$4

sudo sed -e "s/<ORG_NAME>/$ORG/g" -e "s/<REPO_NAME>/$REPO/g" -e "s/<BRANCH_NAME>/$BRANCH/g" -e "s/<PORT>/$PORT/g" sites-available/dev-gen-template.conf > sites-available/dev-gen-${ORG}-${REPO}-${BRANCH}.conf
sudo ln -f -s ../sites-available/dev-gen-${ORG}-${REPO}-${BRANCH}.conf sites-enabled/dev-gen-${ORG}-${REPO}-${BRANCH}.conf
sudo service nginx reload





