#!/bin/sh

BASE_PATH="/vagrant"
TEMP_DIR="${BASE_PATH}/tmp"
APPIDS="10521bb3a18b573f088f84e59c9bbb6c2e2a1a67"

title="printf '\033]2;%s\033\\'"

run_router="$title 'router'; python ${BASE_PATH}/edge-router-avahi.py 2>&1 | tee ${BASE_PATH}/router.log"
run_store="$title 'store'; python ${BASE_PATH}/ostree-store.py -r repo -t ${TEMP_DIR} 2>&1 | tee ${BASE_PATH}/store.log"
run_dbus_consumer="$title 'dbus'; python ${BASE_PATH}/simulate-dbus-consumer.py $APPIDS 2>&1 | tee ${BASE_PATH}/dbus.log"

nfd-stop
rm -rf ${TEMP_DIR}/*

export PYTHONPATH=${BASE_PATH}

tmux new -d -s my-session 'nfd-start; sleep infinity' \; \
     split-window -d "$run_router" \; \
     split-window -d "$run_store" \; \
     split-window -d "$run_dbus_consumer" \; \
     select-layout tiled \; \
     attach \;
