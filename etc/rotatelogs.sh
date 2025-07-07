#!/bin/bash

set -e

DATA=LOG_`date +%0Y.%0m.%0d.%0H.%0M.%0S`

DST_LOG_DIR=${OPS_LOG}/${DATA}

mkdir ${DST_LOG_DIR}

mv ${OPS_LOG}/*.log ${DST_LOG_DIR} || true
mv ${OPS_LOG}/*.log.* ${DST_LOG_DIR} 2>/dev/null || true
mv ${OPS_LOG}/*.log.*.gz ${DST_LOG_DIR} 2>/dev/null || true
