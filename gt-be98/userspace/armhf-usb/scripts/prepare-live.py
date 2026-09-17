#!/usr/bin/env python3
"""Package immutable USB runtime plus bounded, previously validated probes."""
import gzip,hashlib,json,tarfile
from pathlib import Path
r=Path(__file__).resolve().parents[1];w=r.parent
m=json.loads((r/'evidence/payload.json').read_text())
with tarfile.open(r/'armhf-usb-payload.tar','w') as t:
 def owned(x):x.uid=x.gid=0;x.uname=x.gname='root';return x
 t.add(r/'usb-payload/system-libs',arcname='system-libs',filter=owned)
raw=gzip.decompress((w/'a53-runtimes-20260916/build/guest.cpio.gz').read_bytes());pos=0
probes=['runtime-armhf','exception-armhf','throw-armhf.so','cxx-armhf-abi0','cxx-armhf-abi1']
out=r/'build/live';out.mkdir(exist_ok=False)
while pos<len(raw):
 f=[int(raw[pos+6+8*i:pos+14+8*i],16) for i in range(13)]
 name=raw[pos+110:pos+109+f[11]].decode();start=(pos+110+f[11]+3)&~3
 if name in probes:(out/name).write_bytes(raw[start:start+f[6]]);(out/name).chmod(f[1]&0o7777)
 if name=='TRAILER!!!':break
 pos=(start+f[6]+3)&~3
for name in probes:assert (out/name).is_file()
checks=''.join(v['sha256']+'  '+m['link_target']+'/'+k+'\n' for k,v in m['files'].items() if v['kind']=='file')
(out/'payload.sha256').write_text(checks)
(out/'probes.sha256').write_text(''.join(hashlib.sha256((out/n).read_bytes()).hexdigest()+'  '+n+'\n' for n in probes))
script='''#!/bin/sh
set -eu
umask 022
export PATH=/usr/bin:/usr/sbin:/bin:/sbin
unset LD_LIBRARY_PATH LD_PRELOAD
ulimit -c 0
work=/tmp/leon-armhf-usb-20260917
cd "$work"
[ "$(nvram get productid)" = GT-BE98 ]
[ "$(uname -r)" = 4.19.294 ]
awk '$2=="/tmp/mnt/JFFS" && $3=="btrfs" && $4 !~ /noexec/{ok=1}END{exit !ok}' /proc/mounts
printf '%s  %s\\n' '@TARSHA@' armhf-usb-payload.tar | sha256sum -c -
sha256sum -c probes.sha256
bcm_bootstate >bootstate-before.txt
/bin/fc status >acceleration-before.txt
sha256sum /usr/lib/arm-linux-gnueabihf/* >internal-before.sha256
for d in /tmp/mnt/JFFS/system-libs /tmp/mnt/JFFS/system-libs/gt-be98; do
 [ ! -L "$d" ]
 mkdir -p "$d"
done
parent=/tmp/mnt/JFFS/system-libs/gt-be98/@VERSION@
target=@TARGET@
[ ! -L "$parent" ]
if [ ! -e "$parent" ]; then
 stage=$(mktemp -d /tmp/mnt/JFFS/.armhf-stage.XXXXXX)
 trap 'rm -rf "$stage"' EXIT HUP INT TERM
 tar -xf armhf-usb-payload.tar -C "$stage"
 [ -d "$stage/system-libs/gt-be98/@VERSION@/arm-linux-gnueabihf" ]
 mv "$stage/system-libs/gt-be98/@VERSION@" "$parent"
 rm -rf "$stage"
 trap - EXIT HUP INT TERM
fi
[ -d "$target" ] && [ ! -L "$target" ]
[ "$(readlink "$target/libstdc++.so.6")" = libstdc++.so.6.0.34 ]
sha256sum -c payload.sha256
loader="$target/ld-linux-armhf.so.3"
"$loader" --inhibit-cache --library-path "$target" --list "$work/runtime-armhf"
EXPECTED_TRIPLET=arm-linux-gnueabihf /usr/gnu/bin/timeout 20 "$loader" --inhibit-cache --library-path "$target" "$work/runtime-armhf"
/usr/gnu/bin/timeout 20 "$loader" --inhibit-cache --library-path "$target" "$work/exception-armhf" "$work/throw-armhf.so"
for abi in 0 1; do
 EXPECTED_TRIPLET=arm-linux-gnueabihf /usr/gnu/bin/timeout 20 "$loader" --inhibit-cache --library-path "$target" "$work/cxx-armhf-abi$abi"
done
sha256sum -c internal-before.sha256
bcm_bootstate >bootstate-after.txt
cmp bootstate-before.txt bootstate-after.txt
/bin/fc status >acceleration-after.txt
cat acceleration-before.txt acceleration-after.txt
sync
echo LIVE_ARMHF_USB_PAYLOAD_PASS
'''
script=script.replace('@TARGET@',m['link_target']).replace('@VERSION@',m['tree_sha256'][:16]).replace('@TARSHA@',hashlib.sha256((r/'armhf-usb-payload.tar').read_bytes()).hexdigest())
(out/'install-test.sh').write_text(script)
with tarfile.open(r/'live-probes.tar','w') as t:
 for p in out.iterdir():t.add(p,arcname=p.name,filter=owned)
print('LIVE_PAYLOAD_READY',m['link_target'])
