#!/bin/sh
# create new overlayfs to use with systemd-nspawn
set -e
set -x
name=$1

srcdir=`realpath $0`
srcdir=`dirname ${srcdir}`
basedir=${srcdir}/${name}

test -n "${name}" || (echo "No name provided: Usage $0 name"; exit 1);

trap "umount ${basedir}/checkout/etc && umount ${basedir}/checkout" EXIT
shift

for d in up work checkout; do mkdir -p ${basedir}/${d}; done
mount -t overlay overlay -olowerdir=checkout,upperdir=${basedir}/up,workdir=${basedir}/work ${basedir}/checkout
mount -o bind ${basedir}/checkout/usr/etc ${basedir}/checkout/etc
systemd-nspawn -D ${basedir}/checkout --network-zone=ndn -n --machine=${name} --bind $PWD/system:/etc/systemd/system $@

