#!/usr/bin/bash
set -euo pipefail
export LC_ALL=C
work=$(mktemp -d /run/leon-shell-XXXXXX)
trap 'rm -r "$work"' EXIT
cd "$work"
a=(alpha beta gamma);declare -A map=([alpha]=one [beta]=two)
[[ ${a[1]} == beta && ${map[alpha]} == one ]]
mapfile -t lines < <(printf 'first\nsecond\n')
[[ ${lines[1]} == second ]]
[[ 'kernel=4.19.294' =~ kernel=([0-9]+)\.([0-9]+) ]]
[[ ${BASH_REMATCH[1]} == 4 && ${BASH_REMATCH[2]} == 19 ]]
exec {fd}>dynamic-fd
printf '%s\n' 'dynamic descriptor' >&$fd
exec {fd}>&-
[[ $(<dynamic-fd) == 'dynamic descriptor' ]]
value=$(false | true; printf '%s' "$?")
[[ $value == 1 ]]
trap 'printf exit-trap >trap.out' USR1
kill -USR1 $$
[[ $(<trap.out) == exit-trap ]]
trap - USR1
coproc CHILD { printf 'coprocess-result\n'; read -r ack; [[ $ack == done ]]; }
child_pid=$CHILD_PID
read -r result <&"${CHILD[0]}"
[[ $result == coprocess-result ]]
printf 'done\n' >&"${CHILD[1]}"
wait "$child_pid"
shopt -s extglob
[[ alpha == @(alpha|beta) ]]
[[ $((2**10 + 5)) == 1029 ]]
echo LAB_BASH_ARRAYS_FDS_TRAPS_PIPEFAIL_COPROC_PASS
cu() { local prog=$1;shift; /usr/gnu/bin/coreutils "--coreutils-prog=$prog" "$@"; }
printf abc >input
[[ $(cu sha256sum input | cut -d ' ' -f1) == ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad ]]
cu cp --reflink=auto --preserve=mode,timestamps input copied
cmp input copied
cu chmod 640 copied
[[ $(cu stat -c %a copied) == 640 ]]
cu ln copied hardlink
[[ $(cu stat -c %i copied) == $(cu stat -c %i hardlink) ]]
cu ln -s copied symlink
[[ $(cu readlink symlink) == copied ]]
cu base64 input >encoded
cu base64 -d encoded >decoded
cmp input decoded
printf '9\n2\n9\n1\n' | cu sort -nu >sorted
[[ $(<sorted) == $'1\n2\n9' ]]
[[ $(cu date -u -d @0 +%Y-%m-%d) == 1970-01-01 ]]
cu dd if=/dev/zero of=sparse bs=1 count=0 seek=1048576 status=none
[[ $(cu stat -c %s sparse) == 1048576 ]]
cu truncate -s 32 sparse
[[ $(cu stat -c %s sparse) == 32 ]]
cu mv copied moved
cmp moved input
cu rm moved symlink hardlink
[[ ! -e moved ]]
echo LAB_COREUTILS_IO_HASH_SORT_TIME_LINKS_PASS
