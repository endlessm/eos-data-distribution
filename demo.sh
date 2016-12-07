#!/bin/sh

BASE_PATH="."

TEMP_DIR="${BASE_PATH}/tmp"
APPIDS="10521bb3a18b573f088f84e59c9bbb6c2e2a1a67"

title="printf '\033]2;%s\033\\'"

flamegraph () {
        n=$1
        shift 1
        echo "python -m flamegraph -o $n.log $n.py $@"
}

cprofile ()  {
        n=$1
        shift 1
        echo "python -m cProfile -o $n.cprof $n.py $@"
}

run () {
        t=$1
        shift 1
        echo "$title '$t'; $(cprofile ${BASE_PATH}/$@) 2>&1 | tee ${BASE_PATH}/$t.log; sleep infinity"
}

run_router="$(run router edge-router-avahi)"
run_store="$(run store ostree-store -t ${TEMP_DIR})"
run_dbus_consumer="$(run dbus simulate-dbus-consumer $APPIDS)"
run_usb_mock="$(run usb mock-usb-producer ${BASE_PATH}/DL)"

killall tmux;

rm -rf ${TEMP_DIR}/*

export PYTHONPATH=${BASE_PATH}

tmux new -d -s my-session 'watch -d nfd-status; sleep infinity' \; \
     split-window -d "$run_router" \; \
     select-layout tiled \; \
     split-window -d "$run_usb_mock" \; \
     select-layout tiled \; \
     split-window -d "$run_dbus_consumer" \; \
     select-layout tiled \; \
     split-window -d "$run_store" \; \
     select-layout tiled \; \
     attach \;

#
