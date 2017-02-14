#!/bin/sh
# create new overlayfs to use with systemd-nspawn
set -e
set -x
name=$1

test -n "${name}" || (echo "No name provided: Usage $0 name"; exit 1);

trap "sudo umount ${name}/checkout" EXIT

for d in up work checkout; do mkdir -p ${name}/${d}; done
sudo mount -t overlay overlay -olowerdir=checkout,upperdir=${name}/up,workdir=${name}/work ${name}/checkout
sudo systemd-nspawn -D ${name}/checkout --network-zone=ndn -n --machine=${name}-nspawn --bind $PWD/checkout/usr/etc:/etc --bind $PWD/system:/etc/systemd/system

