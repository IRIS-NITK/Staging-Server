#!/bin/bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver 0.0.0.0:8000 > staging_logs.out
gunicorn --bind 0.0.0.0:8000 --workers 3 stagingserver.wsgi:application