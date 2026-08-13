#!/bin/sh
set -eu

python manage.py migrate --noinput

if [ "${LOAD_INITIAL_DATA:-1}" = "1" ]; then
    python manage.py load_initial_content
fi

exec "$@"
