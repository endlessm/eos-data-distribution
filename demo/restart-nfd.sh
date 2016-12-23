#!/bin/sh
BASE_PATH=`realpath ../`

TEMP_DIR="${BASE_PATH}/tmp"

title="printf '\033]2;%s\033\\'"

run_python ()  {
        n=$1
        shift 1
        echo "python $n.py $@"
}

run () {
        t=$1
        shift 1
        echo "$title '$t'; $(run_python ${BASE_PATH}/$@) 2>&1 | tee ${BASE_PATH}/$t.log; sleep infinity"
}

run_store="$(run store eosdatadistribution/store/ostree_store -t ${TEMP_DIR})"
run_dbus="$(run dbus dbus-service)"

nfd-stop
killall tmux;
rm -rf ${TEMP_DIR}/*

sudo nfd-start && sleep 2
nfdc set-strategy /endless/soma/v1 ndn:/localhost/nfd/strategy/multicast/%FD%01

export PYTHONPATH=${BASE_PATH}
tmux new -d -s my-session 'watch -d nfd-status -rsv; sleep infinity' \; \
     split-window -d "$run_store" \; \
     select-layout tiled \; \
     split-window -d "$run_dbus" \; \
     select-layout tiled \; \
     attach \;

