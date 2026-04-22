#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

mkdir -p static
mkdir -p staticfiles
mkdir -p media

python manage.py collectstatic --no-input
python manage.py migrate
