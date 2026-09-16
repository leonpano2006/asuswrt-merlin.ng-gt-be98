#!/usr/bin/env python3
"""Make a lab-only SquashFS and initramfs, never a flashable firmware package."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import stat
import subprocess

r = Path(__file__).resolve().parents[1]
w = r.parent
parser = argparse.ArgumentParser()
parser.add_argument('--revision', default='')
args = parser.parse_args()
assert not args.revision or args.revision.replace('-', '').isalnum()
outdir = r / 'build' / args.revision
outdir.mkdir(parents=True, exist_ok=True)
root = outdir / 'rootfs'
base = w / 'rootfs-no-adsl-20260916/build/unpacked-rootfs'
assert not root.exists()
subprocess.run(['cp', '-a', '--reflink=auto', str(base), str(root)], check=True)
shutil.copytree(r / 'overlay', root, dirs_exist_ok=True, symlinks=True)
for p in base.rglob('*'):
    if p.is_dir() and not p.is_symlink():
        shutil.copystat(p, root / p.relative_to(base), follow_symlinks=False)
# Only the lab's early boot changes /run; ASUS rc is never executed in this guest.
assert (root / 'run').is_symlink()
(root / 'run').unlink()
(root / 'run').mkdir()
units = root / 'usr/lib/systemd/system'
units.mkdir(parents=True)
source = next((r / 'sources').glob('systemd-stable-*'))
for name in ('poweroff.target', 'systemd-poweroff.service', 'shutdown.target', 'umount.target', 'final.target',
             'systemd-journald.socket', 'systemd-journald-dev-log.socket'):
    shutil.copy2(source / 'units' / name, units / name)
for name in ('basic.target', 'sysinit.target', 'sockets.target', 'local-fs.target', 'swap.target', 'paths.target', 'timers.target'):
    (units / name).write_text('[Unit]\nDescription=Offline lab ' + name + '\nDefaultDependencies=no\n')
(units / 'tmp.mount').write_text('''[Unit]
Description=ASUS temporary files and live /etc configuration
DefaultDependencies=no
Before=local-fs.target
[Mount]
What=tmpfs
Where=/tmp
Type=tmpfs
Options=mode=1777
''')
(units / 'systemd-journald.service').write_text('''[Unit]
Description=Offline lab journal
DefaultDependencies=no
Requires=systemd-journald.socket systemd-journald-dev-log.socket
After=systemd-journald.socket systemd-journald-dev-log.socket
[Service]
Type=notify
ExecStart=/usr/lib/systemd/systemd-journald
FileDescriptorStoreMax=4224
RuntimeDirectory=systemd/journal
RuntimeDirectoryPreserve=yes
Sockets=systemd-journald.socket systemd-journald-dev-log.socket
StandardOutput=null
Restart=on-failure
''')
(units / 'leon-lab.target').write_text('''[Unit]
Description=GT-BE98 offline PID 1 lab
DefaultDependencies=no
Requires=leon-check.service
After=leon-check.service
''')
(units / 'leon-check.service').write_text('''[Unit]
Description=Offline systemd integration checks
DefaultDependencies=no
Requires=systemd-journald.service
After=systemd-journald.service
Conflicts=shutdown.target
Before=shutdown.target
[Service]
Type=oneshot
ExecStart=/usr/libexec/leon-systemd-lab-check
SuccessExitStatus=SIGTERM
StandardOutput=tty
StandardError=tty
TTYPath=/dev/console
TimeoutStartSec=90
''')
(units / 'leon-worker.service').write_text('''[Unit]
Description=Restart and cgroup integration probe
DefaultDependencies=no
Requires=systemd-journald.service
After=systemd-journald.service
Conflicts=shutdown.target
Before=shutdown.target
[Service]
Type=simple
ExecStart=/bin/sh -c 'echo LEON_WORKER_STARTED; exec /bin/sleep 300'
Restart=on-failure
RestartSec=100ms
MemoryAccounting=yes
MemoryMax=64M
TasksMax=16
Delegate=yes
StandardOutput=journal
''')
check = root / 'usr/libexec/leon-systemd-lab-check'
check.parent.mkdir(exist_ok=True)
shutil.copy2(r / 'scripts/lab-check.sh', check)
check.chmod(0o755)
shutil.copy2(r / 'build/probes/guardcheck', root / 'usr/libexec/leon-systemd-guardcheck')
provider = root / 'usr/lib/arm-linux-gnueabi/leon-systemd-lab'
provider.mkdir()
shutil.copy2(r / 'build/probes/libguard-provider.so', provider / 'libguard-provider.so')
(units / 'leon-guard.service').write_text('''[Unit]
Description=Offline ARMEL trial-guard integration probe
DefaultDependencies=no
[Service]
Type=oneshot
Environment=LD_PRELOAD=/usr/lib/arm-linux-gnueabi/leon-trial-bootguard.so
ExecStart=@/usr/libexec/leon-systemd-guardcheck /sbin/init
RemainAfterExit=yes
StandardOutput=tty
StandardError=tty
TTYPath=/dev/console
''')
squash = outdir / 'systemd-lab.squashfs'
assert not squash.exists()
with (r / 'evidence' / ('lab-squashfs-' + (args.revision or 'first') + '.log')).open('w') as log:
    subprocess.run(['nice', '-n', '10', 'mksquashfs', str(root), str(squash), '-noappend', '-all-root',
        '-comp', 'zstd', '-Xcompression-level', '22', '-b', '1048576', '-tailends',
        '-processors', '4', '-mem', '512M', '-mkfs-time', '1789556948', '-no-progress', '-exit-on-error'],
        stdout=log, stderr=subprocess.STDOUT, check=True)
old = w / 'a53-runtimes-20260916/build/guest.cpio.gz'
assert hashlib.sha256(old.read_bytes()).hexdigest() == '4a4bebee33080471d2a204269095d7869c7c0169a4fe9d76dae8117b9d337dae'
raw = gzip.decompress(old.read_bytes())
pos = 0
busybox = None
while pos < len(raw):
    assert raw[pos:pos+6] == b'070701'
    fields = [int(raw[pos+6+8*i:pos+14+8*i], 16) for i in range(13)]
    size, namesize = fields[6], fields[11]
    name = raw[pos+110:pos+110+namesize-1].decode()
    start = (pos+110+namesize+3) & ~3
    if name == 'bin/busybox': busybox = raw[start:start+size]; break
    pos = (start+size+3) & ~3
assert busybox
entries = {name: (stat.S_IFDIR | 0o755, b'', 0, 0) for name in ('bin', 'dev', 'proc', 'sys', 'tmp', 'newroot')}
entries.update({'bin/busybox': (stat.S_IFREG | 0o755, busybox, 0, 0),
    'init': (stat.S_IFREG | 0o755, (r / 'scripts/guest-init.sh').read_bytes(), 0, 0),
    'rootfs.squashfs': (stat.S_IFREG | 0o444, squash.read_bytes(), 0, 0),
    'dev/console': (stat.S_IFCHR | 0o600, b'', 5, 1),
    'dev/null': (stat.S_IFCHR | 0o666, b'', 1, 3),
    'dev/loop0': (stat.S_IFBLK | 0o600, b'', 7, 0),
    'TRAILER!!!': (0, b'', 0, 0)})
out = bytearray()
for ino, (name, (mode, data, major, minor)) in enumerate(entries.items(), 1):
    name = name.encode() + b'\0'
    fields = [ino, mode, 0, 0, 2 if stat.S_ISDIR(mode) else 1, 0, len(data), 0, 0, major, minor, len(name), 0]
    out += b'070701' + ''.join(f'{x:08x}' for x in fields).encode() + name
    out += b'\0' * (-len(out) % 4)
    out += data
    out += b'\0' * (-len(out) % 4)
guest = outdir / 'guest.cpio.gz'
guest.write_bytes(gzip.compress(out, compresslevel=1, mtime=0))
(r / 'evidence' / ('guest-inputs-' + (args.revision or 'first') + '.json')).write_text(json.dumps({'rootfs_sha256': hashlib.sha256(squash.read_bytes()).hexdigest(),
    'rootfs_bytes': squash.stat().st_size, 'additional_compressed_bytes': squash.stat().st_size - 74629120,
    'guest_sha256': hashlib.sha256(guest.read_bytes()).hexdigest(), 'lab_only': True,
    'asus_rc_executed': False, 'flashable_package_created': False}, indent=2) + '\n')
print('SYSTEMD_LAB_GUEST_READY', squash.stat().st_size, guest.stat().st_size, flush=True)
