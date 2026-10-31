#!/usr/bin/env bash

# Stop the build immediately if any command fails.
set -o errexit

# Install the exact application dependencies committed in requirements.txt.
python -m pip install -r requirements.txt

# Build Django's production static-file manifest.
python manage.py collectstatic --no-input

# Apply database migrations during deployment.
python manage.py migrate

# Create the initial Django superuser, or skip if one already exists.
python create_superuser.py