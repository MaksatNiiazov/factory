#!/bin/bash

set -e

APP_NAME=ops
DB_NAME=ops
APP_ROOT=${OPS_ROOT}
PG_DUMP_PARAMS=""
RSYNC_PARAMS="--exclude __pycache__"
BACKUPS_PATH=${OPS_BACKUPS}
BACKUPS_OLD_DAYS=14

# ---

if [ -z "${APP_ROOT}" ]; then
    echo "APP_ROOT is empty"
    exit 1
fi

if [ -z "${BACKUPS_PATH}" ]; then
    echo "BACKUPS_PATH is empty"
    exit 1
fi

if [ ! -d "${BACKUPS_PATH}" ]; then
    echo "BACKUPS_PATH=${BACKUPS_PATH} doesnt exist"
    exit 1
fi

ARCH_NAME=${APP_NAME}_`date +%0Y.%0m.%0d.%0H.%0M`
ARCH_PATH=${BACKUPS_PATH}/${ARCH_NAME}
DB_BACKUP_FILE=${ARCH_PATH}/${ARCH_NAME}.backup

# make dir
echo "* make ${ARCH_PATH} ..."
mkdir -p ${ARCH_PATH}

# delete old backups
echo "* delete old (${BACKUPS_OLD_DAYS} days) backups from ${BACKUPS_PATH} ..."
find ${BACKUPS_PATH} -maxdepth 1 -name "${APP_NAME}_????.??.??.??.??" -mtime +${BACKUPS_OLD_DAYS} -type d  -print -exec rm -rf {} \;

# db backup to file
echo "* db ${DB_NAME} backup to ${DB_BACKUP_FILE} ..."
pg_dump -Z0 ${PG_DUMP_PARAMS} ${DB_NAME} > ${DB_BACKUP_FILE} &

# copy app-files
echo "* rsync ${APP_ROOT} -> ${ARCH_PATH} ..."
rsync -av --progress ${APP_ROOT} ${ARCH_PATH} ${RSYNC_PARAMS} > ${ARCH_PATH}/rsync.log &

# wait pg_dump+rsync
echo "* wait pg_dump+rsync ..."
wait

# gzip backup file - background
echo "* gzip backup (background) ..."
nohup gzip --fast ${DB_BACKUP_FILE} &

# tar.gz app-files
FILES_BASENAME=`basename ${APP_ROOT}`  # i.e. "simpleloan_back"
FILES_PATH=${ARCH_PATH}/${FILES_BASENAME}
FILES_DSTFILENAME=${FILES_PATH}.tar.gz
echo "* gzip files ${FILES_PATH} -> ${FILES_DSTFILENAME} ..."
SRCSIZE=`du -sb ${FILES_PATH} | grep -o '[0-9]*\s'`
tar -C ${ARCH_PATH} -cf - $FILES_BASENAME | pv -s $SRCSIZE | gzip --fast > ${FILES_DSTFILENAME}

# remove nonarch app-files - background
echo "* remove ${FILES_PATH} (background) ..."
nohup rm -rf ${FILES_PATH} &
