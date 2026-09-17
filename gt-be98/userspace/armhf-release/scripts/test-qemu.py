#!/usr/bin/env python3
"""Verify external ARMHF link before/after a simulated USB mount on kernel #36."""
import gzip,hashlib,json,stat,subprocess,sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
r=Path(__file__).resolve().parents[1];w=r.parent
sys.path.insert(0,str(w/'multiarch-loader-20260916/scripts'))
from common import inventory
root=r/'build/rootfs';image=r/'build/final-leon6-v2.squashfs'
unpacked=r/'build/unpacked-v2';assert not unpacked.exists()
with (r/'evidence/unpack.log').open('w') as log:
 subprocess.run(['unsquashfs','-no-progress','-processors','4','-d',str(unpacked),str(image)],stdout=log,stderr=subprocess.STDOUT,check=True)
assert inventory(root)==inventory(unpacked)
manifest=json.loads((w/'armhf-usb-20260917/evidence/payload.json').read_text())
raw=gzip.decompress((w/'a53-runtimes-20260916/build/guest.cpio.gz').read_bytes());pos=0;old={}
while pos<len(raw):
 f=[int(raw[pos+6+8*i:pos+14+8*i],16) for i in range(13)]
 name=raw[pos+110:pos+109+f[11]].decode();start=(pos+110+f[11]+3)&~3
 old[name]=(f[1],raw[start:start+f[6]],f[9],f[10])
 if name=='TRAILER!!!':break
 pos=(start+f[6]+3)&~3
entries={d:(stat.S_IFDIR|0o755,b'',0,0) for d in ['bin','dev','proc','sys','tmp','newroot','usb-image']}
probes=[name for name in old if name.startswith(('runtime-','exception-','throw-','cxx-'))]
for name in ['bin/busybox',*probes]:entries[name]=old[name]
for p in sorted((w/'armhf-usb-20260917/usb-payload').rglob('*')):
 name='usb-image/'+p.relative_to(w/'armhf-usb-20260917/usb-payload').as_posix();mode=p.lstat().st_mode
 data=str(p.readlink()).encode() if p.is_symlink() else p.read_bytes() if p.is_file() else b''
 entries[name]=(mode,data,0,0)
executables=[]
for p in root.rglob('*'):
 if p.is_symlink() or not p.is_file():continue
 with p.open('rb') as f:
  if f.read(4)!=b'\x7fELF':continue
  f.seek(0);e=ELFFile(f)
  interp=[s.get_interp_name() for s in e.iter_segments() if s.header.p_type=='PT_INTERP']
  if interp:executables.append(interp[0]+' /'+p.relative_to(root).as_posix()+'\n')
assert not any('armhf' in s for s in executables)
entries['executables.txt']=(stat.S_IFREG|0o444,''.join(sorted(executables)).encode(),0,0)
init='''#!/bin/busybox sh
set -eu
export PATH=/bin
/bin/busybox --install -s /bin
exec </dev/console >/dev/console 2>&1
echo QEMU_LAB_INIT_REACHED
trap 'echo LAB_ARMHF_FAILURE; poweroff -f' EXIT
mount -t proc proc /proc
mount -t sysfs sysfs /sys
losetup -r /dev/loop0 /rootfs.squashfs
mount -t squashfs -o ro /dev/loop0 /newroot
mount -t devtmpfs devtmpfs /newroot/dev
mount -t tmpfs tmpfs /newroot/tmp
mkdir -p /newroot/tmp/etc /newroot/tmp/mnt/JFFS /newroot/tmp/probes
for p in /newroot/rom/etc/*; do ln -s /rom/etc/${p##*/} /newroot/tmp/etc/${p##*/}; done
unset LD_LIBRARY_PATH LD_PRELOAD
test -L /newroot/usr/lib/arm-linux-gnueabihf
# Absolute symlinks are resolved inside the new root, never by the host shell.
if chroot /newroot /lib/ld-linux-armhf.so.3 --version >/tmp/absent.log 2>&1; then exit 1; fi
count=0
while read -r loader program; do
 if ! chroot /newroot "$loader" --inhibit-cache --list "$program" >/tmp/loader.log 2>&1; then
  echo "LAB_LOADER_FAIL $program"; cat /tmp/loader.log; exit 1
 fi
 count=$((count+1))
done </executables.txt
echo "LAB_WITHOUT_USB_ALL_NATIVE_ARMEL_LOADERS_PASS count=$count"
# Reproduce the externally mounted USB directory without exposing host disks.
mount -t tmpfs usb-simulation /newroot/tmp/mnt/JFFS
cp -a /usb-image/system-libs /newroot/tmp/mnt/JFFS/
for p in /runtime-* /exception-* /throw-* /cxx-*; do cp "$p" /newroot/tmp/probes/; done
chroot /newroot /lib/ld-linux-armhf.so.3 --version | head -1
chroot /newroot /lib/ld-linux-armhf.so.3 --inhibit-cache --list /tmp/probes/runtime-armhf
run_probes() {
 for abi in aarch64 armel armhf armel-legacy aarch64-legacy; do
  case "$abi" in aarch64*) triplet=aarch64-linux-gnu;; armel*) triplet=arm-linux-gnueabi;; armhf) triplet=arm-linux-gnueabihf;; esac
  EXPECTED_TRIPLET=$triplet chroot /newroot /tmp/probes/runtime-$abi
  chroot /newroot /tmp/probes/exception-$abi /tmp/probes/throw-$abi.so
  EXPECTED_TRIPLET=$triplet chroot /newroot /tmp/probes/cxx-$abi-abi0
  EXPECTED_TRIPLET=$triplet chroot /newroot /tmp/probes/cxx-$abi-abi1
  echo LAB_RUNTIME_${abi}_PASS
 done
}
run_probes
echo LAB_ARMHF_USB_NOCACHE_PASS
chroot /newroot /usr/sbin/ldconfig
run_probes
echo LAB_ARMHF_USB_CACHE_PASS
chroot /newroot /usr/bin/zstd --help >/tmp/zstd-help
chroot /newroot /usr/bin/zstd --ultra -22 -T2 -q -c /usr/share/leon-upstream.json >/newroot/tmp/meta.zst
chroot /newroot /usr/bin/zstd -q -d -c /tmp/meta.zst >/tmp/meta.json
cmp /tmp/meta.json /newroot/usr/share/leon-upstream.json
chroot /newroot /usr/bin/zstd --format=gzip -q -c /usr/share/leon-upstream.json >/newroot/tmp/meta.gz
chroot /newroot /usr/bin/zstd -q -d -c /tmp/meta.gz >/tmp/meta-gzip.json
cmp /tmp/meta-gzip.json /newroot/usr/share/leon-upstream.json
echo LAB_DYNAMIC_ZSTD_PASS
chroot /newroot /usr/gnu/bin/sqlite3 /tmp/check.db "pragma journal_mode=WAL; create virtual table s using fts5(t); insert into s values('armhf external'); select t from s where s match 'external'; pragma integrity_check;" >/tmp/sqlite-result
grep -q 'armhf external' /tmp/sqlite-result
grep -q '^ok$' /tmp/sqlite-result
echo LAB_SQLITE_PASS
chroot /newroot /usr/libexec/openssl4 version
chroot /newroot /usr/sbin/openssl version
echo LAB_DUAL_OPENSSL_PASS
# A complete process exit precedes the simulated unplug test.
umount /newroot/tmp/mnt/JFFS
if chroot /newroot /tmp/probes/runtime-armhf >/tmp/absent2.log 2>&1; then exit 1; fi
chroot /newroot /bin/busybox true
chroot /newroot /usr/bin/systemctl --version | head -1
echo LAB_ARMHF_ABSENT_NATIVE_STILL_RUNS_PASS
echo LAB_ARMHF_ALL_PASS
trap - EXIT
poweroff -f
'''
entries.update({'init':(stat.S_IFREG|0o755,init.encode(),0,0),'rootfs.squashfs':(stat.S_IFREG|0o444,image.read_bytes(),0,0),
 'dev/console':(stat.S_IFCHR|0o600,b'',5,1),'dev/loop0':(stat.S_IFBLK|0o600,b'',7,0),'TRAILER!!!':(0,b'',0,0)})
out=bytearray()
for ino,(name,(mode,data,major,minor)) in enumerate(entries.items(),1):
 n=name.encode()+b'\0';fields=[ino,mode,0,0,2 if stat.S_ISDIR(mode) else 1,0,len(data),0,0,major,minor,len(n),0]
 out+=b'070701'+''.join(f'{x:08x}' for x in fields).encode()+n
 out+=b'\0'*(-len(out)%4);out+=data;out+=b'\0'*(-len(out)%4)
guest=r/'build/guest.cpio.gz';guest.write_bytes(gzip.compress(out,compresslevel=1,mtime=0))
(r/'scripts/run-qemu.py').write_text((w/'rootfs-size-20260916/scripts/run-qemu.py').read_text())
subprocess.run(['python3',str(r/'scripts/run-qemu.py'),'--label','armhf-usb-v2','--kernel',str(w/'multiarch-loader-20260916/saved-inputs/Image36'),'--initrd',str(guest),'--complete-marker','reboot: Power down','--timeout','180'],check=True)
result=json.loads((r/'builds/qemu/armhf-usb-v2/result.json').read_text())
assert 'LAB_ARMHF_ALL_PASS' in result['lab_lines'] and 'LAB_ARMHF_FAILURE' not in result['lab_lines']
(r/'evidence/qemu-verification.json').write_text(json.dumps({'rootfs_bytes_modes_links_verified':True,'loader_checks_without_usb':len(executables),'all_five_runtime_probe_sets_passed_before_and_after_cache':True,'dynamic_zstd_sqlite_dual_openssl_passed':True,'router_modified':False,'usb_filesystem_simulated_with_tmpfs':True},indent=2)+'\n')
print('ARMHF_LINK_QEMU_PASS')
