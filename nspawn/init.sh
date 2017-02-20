#!/bin/sh
# Init OSTree Repo

srcdir=`realpath $0`
srcdir=`dirname ${srcdir}`
repodir=${srcdir}/repo
checkoutdir=${srcdir}/checkout

mkdir -p ${repodir}
ostree --repo=${repodir} init --mode=bare
ostree --repo=${repodir} remote add --no-gpg-verify endless https://endless:kassyicNigNarHon@origin.ostree.endlessm.com/staging/dev/eos-amd64
sudo ostree --repo=${repodir} pull endless master/amd64
sudo ostree --repo=${repodir} checkout endless:master/amd64 ${checkoutdir}
