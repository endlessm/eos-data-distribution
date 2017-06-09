#!/bin/sh

BASE_PATH=$1

TEMP_DIR="${BASE_PATH}/tmp"
APPIDS="10521bb3a18b573f088f84e59c9bbb6c2e2a1a67"

title="printf '\033]2;%s\033\\'"

flamegraph () {
        n=$1
        shift 1
        echo "python -m flamegraph -o $n.log $n.py -vvv $@"
}

cprofile ()  {
        n=$1
        shift 1
        echo "python -m cProfile -o $(basename $n).cprof $n.py -vvv $@"
}

run () {
        t=$1
        shift 1
        echo "$title '$t'; $(cprofile ${BASE_PATH}/$@) 2>&1 | tee ${BASE_PATH}/$t.log; sleep infinity"
}

run_router="$(run router eos_data_distribution/producers/soma_subscriptions)"
run_store="sleep 1 && $(run store eos_data_distribution/store/ostree_store -t ${TEMP_DIR})"
run_dbus_consumer="sleep 2 && $(run dbus demo/simulate-dbus-consumer $APPIDS)"
run_usb_mock="$(run usb demo/mock-usb-producer ${BASE_PATH}/DL)"

killall tmux;

mkdir -p ${BASE_PATH}/tmp
mkdir -p ${BASE_PATH}/DL

export PYTHONPATH=${BASE_PATH}

tmux new -d -s my-session \
     "$run_router" \; \
     select-layout tiled \; split-window -d \
     "$run_dbus_consumer" \; \
     select-layout tiled \; split-window -d \
     "$run_store" \; \
     select-layout tiled \; \
     attach \;
     #     'watch -d nfd-status; sleep infinity' \; \
         #     split-window -d \
         #     "$run_usb_mock" \; \
         #     select-layout tiled \; split-window -d \
         #
