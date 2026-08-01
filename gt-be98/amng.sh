#!/bin/bash
# Asuswrt-Merlin (gnuton fork) build container runner — GT-BE98 / HND 5.04 BE 4916
#
# Usage:
#   ./amng.sh                       # interactive shell inside the build container
#   ./amng.sh <command...>          # run a command in release/src-rt-5.04behnd.4916
#
# The gnuton toolchain image keeps its toolchains in /home/docker/am-toolchains/brcm-arm-hnd,
# but the tree's platform.mak hardcodes /opt/toolchains — so we symlink it on entry.

set -euo pipefail

SRC_DIR="${AMNG_SRC:-$(cd "$(dirname "$0")/.." && pwd)}"
# amng-toolchains:ccache = the gnuton image with ccache spliced in front of the
# two 4916/BE toolchains (see scratchpad/Dockerfile.ccache). Set AMNG_IMAGE to
# the stock gnuton image to build without ccache.
IMAGE="${AMNG_IMAGE:-amng-toolchains:ccache}"
CCACHE_DIR_HOST="${AMNG_CCACHE:-$HOME/.ccache-amng}"
MOUNT="/build/asuswrt-merlin.ng"
SDK="release/src-rt-5.04behnd.4916"

SETUP='sudo ln -sfn /home/docker/am-toolchains/brcm-arm-hnd /opt/toolchains'

if [ $# -eq 0 ]; then
    INNER="$SETUP; cd '$MOUNT/$SDK'; exec bash"
    TTY="-it"
else
    INNER="$SETUP; cd '$MOUNT/$SDK'; $*"
    TTY="-i"
fi

mkdir -p "$CCACHE_DIR_HOST"

exec docker run --rm $TTY \
    -v "$SRC_DIR:$MOUNT" \
    -v "$CCACHE_DIR_HOST:/ccache" \
    -u docker:docker \
    -w "$MOUNT" \
    -e "TERM=${TERM:-xterm-256color}" \
    "$IMAGE" \
    bash -lc "$INNER"
