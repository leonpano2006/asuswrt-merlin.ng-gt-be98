#!/usr/bin/bash
set -euo pipefail
export PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin
cd /tmp/leon8-probes
for abi in aarch64 armel armhf armel-legacy aarch64-legacy; do
 case "$abi" in aarch64*) triplet=aarch64-linux-gnu;; armel*) triplet=arm-linux-gnueabi;; armhf) triplet=arm-linux-gnueabihf;; esac
 EXPECTED_TRIPLET=$triplet ./runtime-$abi
 ./exception-$abi ./throw-$abi.so
 EXPECTED_TRIPLET=$triplet ./cxx-$abi-abi0
 EXPECTED_TRIPLET=$triplet ./cxx-$abi-abi1
 echo LIVE_RUNTIME_${abi}_PASS
done
/usr/bin/zstd --ultra -22 -T2 -q -c /usr/share/leon-upstream.json > metadata.zst
/usr/bin/zstd -q -d -c metadata.zst > metadata.json
cmp metadata.json /usr/share/leon-upstream.json
/usr/bin/zstd --format=gzip -q -c /usr/share/leon-upstream.json > metadata.gz
/usr/bin/zstd -q -d -c metadata.gz > metadata-gzip.json
cmp metadata-gzip.json /usr/share/leon-upstream.json
/usr/gnu/bin/sqlite3 ./test.db 'pragma journal_mode=WAL; create virtual table s using fts5(t); insert into s values("armhf external"); select t from s where s match "external"; pragma integrity_check;'
/usr/libexec/openssl4 version
/usr/sbin/openssl version
readlink /usr/lib/arm-linux-gnueabihf
readlink -f /usr/lib/arm-linux-gnueabihf/libc.so.6
awk '$2=="/tmp/mnt/JFFS" && $3=="btrfs"{ok=1}END{exit !ok}' /proc/mounts
echo LIVE_LEON8_RUNTIMES_AND_TOOLS_PASS
