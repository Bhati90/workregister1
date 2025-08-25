#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Run database migrations
# echo "Applying database migrations..."
python manage.py migrate

# # Create the superuser using the custom command
# echo "Creating initial superuser..."
python manage.py create_initial_superuser

# Start the Gunicorn web server
echo "Starting Gunicorn server..."
# startup.sh (AFTER)
exec gunicorn labour_crm.wsgi:application --bind 0.0.0.0:${PORT:-8000}