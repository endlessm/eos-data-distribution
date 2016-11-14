#!/bin/sh

BASE_PATH="/vagrant"
TEMP_DIR="${BASE_PATH}/tmp"
APPIDS="10521bb3a18b573f088f84e59c9bbb6c2e2a1a67"

run_router="printf '\033]2;%s\033\\' 'router'; python ${BASE_PATH}/edge-router-avahi.py"
run_store="printf '\033]2;%s\033\\' 'store'; python ${BASE_PATH}/ostree-store.py -r repo -t ${TEMP_DIR}"
run_dbus_consumer="printf '\033]2;%s\033\\' 'dbus'; python ${BASE_PATH}/simulate-dbus-consumer.py $APPIDS"

nfd-stop
rm -rf ${TEMP_DIR}/*

export PYTHONPATH=${BASE_PATH}

tmux new -d -s my-session 'nfd-start; sleep infinity' \; \
     split-window -d "$run_router" \; \
     split-window -d "$run_store" \; \
     split-window -d "$run_dbus_consumer" \; \
     select-layout tiled \; \
     attach \;
