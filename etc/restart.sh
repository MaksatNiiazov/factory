#!/bin/bash

# with param "soft" - fast restart if possible

set -e


echo -e "\033[1mmemcached...\033[0m"
systemctl restart memcached.service


echo -e "\033[1mgunicorn...\033[0m"
systemctl restart ops-gunicorn.service


echo -e "\033[1mdaphne...\033[0m"
systemctl restart ops-daphne.service


echo -e "\033[1mcelery-beat...\033[0m"
systemctl restart ops-celery-beat.service

echo -e "\033[1mcelery-worker...\033[0m"
systemctl restart ops-celery-worker.service


if [[ $1 == "soft" ]]; then
    echo -e "\033[1mnginx (reload)...\033[0m"
	systemctl reload-or-restart nginx.service
else
    echo -e "\033[1mnginx (restart)...\033[0m"
	systemctl restart nginx.service
fi
