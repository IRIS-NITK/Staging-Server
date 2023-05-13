#!/bin/bash
python manage.py migrate
gunicorn --bind 127.0.0.1:7000 --workers 3 stagingserver.wsgi:application