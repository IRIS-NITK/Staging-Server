#!/bin/bash
python manage.py makemigrations
python manage.py migrate --run-syncdb
gunicorn --bind 0.0.0.0:7000 --workers 3 stagingserver.wsgi:application --log-file=-