#!/bin/sh
# Init OSTree Repo

srcdir=`realpath $0`
srcdir=`dirname ${srcdir}`
repodir=${srcdir}/repo
checkoutdir=${srcdir}/checkout

mkdir -p ${repodir}
ostree --repo=${repodir} init --mode=bare
ostree --repo=${repodir} remote add --no-gpg-verify endless https://endless:kassyicNigNarHon@origin.ostree.endlessm.com/staging/dev/eos-amd64
ostree --repo=${repodir} pull endless os/eos/amd64/master
ostree --repo=${repodir} checkout endless:os/eos/amd64/master ${checkoutdir}
