#!/bin/sh
# Init OSTree Repo

mkdir -p repo
ostree --repo=repo init --mode=bare
ostree --repo=repo remote add --no-gpg-verify endless https://endless:kassyicNigNarHon@origin.ostree.endlessm.com/staging/dev/eos-amd64
sudo ostree --repo=repo pull endless master/amd64
sudo ostree --repo=repo checkout endless:master/amd64 checkout
