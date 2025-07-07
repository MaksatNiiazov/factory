#!/bin/bash

set -e

echo -e "\033[1mcelery-beat (background)...\033[0m"
systemctl stop ops-celery-beat.service &

echo -e "\033[1mcelery-worker (background)...\033[0m"
systemctl stop ops-celery-worker.service &

echo -e "\033[1mdaphne (background)...\033[0m"
systemctl stop ops-daphne.service &

echo -e "\033[1mdaphne (background)...\033[0m"
systemctl stop ops-gunicorn.service &

echo -e "\033[1mwait stop services...\033[0m"
wait
