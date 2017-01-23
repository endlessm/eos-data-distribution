ls | grep eos | while read d; do (cd $d; docker build --no-cache -t $d . ); done
