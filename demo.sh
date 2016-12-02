#!/bin/sh

BASE_PATH="/vagrant"
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
        echo "$title '$t'; $(cprofile ${BASE_PATH}/$@) 2>&1 | tee ${BASE_PATH}/$t.log"
}

run_router="$(run router edge-router-avahi)"
run_store="$(run store ostree-store -r repo -t ${TEMP_DIR})"
run_dbus_consumer="$(run dbus simulate-dbus-consumer $APPIDS)"
run_usb_mock="$(run usb mock-usb-producer /vagrant/DL)"

nfd-stop; killall tmux;
rm -rf ${TEMP_DIR}/*

export PYTHONPATH=${BASE_PATH}

tmux new -d -s my-session 'nfd-start; sleep infinity' \; \
     split-window -d "$run_router" \; \
     split-window -d "$run_usb_mock" \; \
     split-window -d "$run_dbus_consumer" \; \
     split-window -d "$run_store" \; \
     select-layout tiled \; \
     attach \;

#
