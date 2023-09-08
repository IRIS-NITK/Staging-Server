#!/bin/bash
python manage.py makemigrations
# python manage.py migrate
python manage.py migrate --run-syncdb
gunicorn --bind 127.0.0.1:7000 --workers 3 stagingserver.wsgi:application