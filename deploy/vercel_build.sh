#!/bin/sh
# Collect static for WhiteNoise during Vercel install/build.
set -e
export DJANGO_SETTINGS_MODULE=config.settings.vercel
export SECRET_KEY="${SECRET_KEY:-vercel-test-only-insecure-key-do-not-use-on-digitalocean}"
python manage.py collectstatic --noinput
