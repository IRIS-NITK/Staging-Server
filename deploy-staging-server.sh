#!/bin/bash

# Activate the virtual environment
source env/bin/activate

# Run the server in the background using nohup and store output in a file
nohup python manage.py runserver 0.0.0.0:8000 > staging_logs.out &

# Start the Celery worker
nohup celery -A stagingserver worker -l info > celery_logs.out &
