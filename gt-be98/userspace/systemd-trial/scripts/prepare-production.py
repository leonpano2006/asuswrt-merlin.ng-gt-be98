#!/usr/bin/env python3
"""Stage real early boot and the ASUS bridge; keep all lab-only units separate."""
from pathlib import Path
import difflib
import json
import shutil
import subprocess
from common import inventory, sha

r = Path(__file__).resolve().parents[1]; w = r.parent
base = w / 'rootfs-no-adsl-20260916/build/unpacked-rootfs'
root = r / 'build/production-rootfs'
assert not root.exists()
subprocess.run(['cp', '-a', '--reflink=auto', str(base), str(root)], check=True)
shutil.copytree(w / 'systemd-lab-20260916/overlay', root, dirs_exist_ok=True, symlinks=True)
(root / 'usr/sbin/rc').unlink()
shutil.copytree(r / 'overlay', root, dirs_exist_ok=True, symlinks=True)
assert (root / 'run').is_symlink(); (root / 'run').unlink(); (root / 'run').mkdir()
targets = json.loads((w / 'a53-runtimes-20260916/configs/build-targets.json').read_text())
command = [targets['aarch64']['cc'], '-Os', '-g', '-Wall', '-Wextra', '-Werror',
           '-frecord-gcc-switches', '-Wl,--build-id=sha1', '-static', '-no-pie',
           str(r / 'src/early-init.c'), '-o', str(r / 'build/early-init')]
subprocess.run(command, check=True)
(r / 'evidence/early-init-command.json').write_text(json.dumps(command, indent=2) + '\n')
subprocess.run(['aarch64-linux-gnu-strip', '--strip-unneeded', '-o', str(root / 'usr/sbin/init'),
                str(r / 'build/early-init')], check=True)
for source, name in [('early-prepare.sh', 'leon-systemd-prepare'), ('local-ready.sh', 'leon-local-ready')]:
    dest = root / 'usr/libexec' / name; dest.parent.mkdir(exist_ok=True)
    shutil.copy2(r / 'scripts' / source, dest); dest.chmod(0o755)
units = root / 'usr/lib/systemd/system'; units.mkdir(exist_ok=True)
old_units = w / 'systemd-lab-20260916/build/guard-service/rootfs/usr/lib/systemd/system'
for name in ('basic.target', 'sysinit.target', 'sockets.target', 'local-fs.target', 'swap.target',
             'paths.target', 'timers.target', 'tmp.mount', 'systemd-journald.service'):
    text = (old_units / name).read_text().replace('Offline lab', 'ASUS compatibility').replace('Offline lab journal', 'System journal')
    (units / name).write_text(text)
upstream = next((w / 'systemd-lab-20260916/sources').glob('systemd-stable-*')) / 'units'
for name in ('poweroff.target', 'systemd-poweroff.service', 'reboot.target', 'systemd-reboot.service',
             'shutdown.target', 'umount.target', 'final.target', 'systemd-journald.socket', 'systemd-journald-dev-log.socket'):
    shutil.copy2(upstream / name, units / name)
(units / 'default.target').symlink_to('leon-router.target')
(units / 'ctrl-alt-del.target').symlink_to('reboot.target')
(units / 'leon-router.target').write_text('''[Unit]
Description=GT-BE98 ASUS compatibility boot
DefaultDependencies=no
Requires=asus-rc.service
Wants=leon-local-ready.service
After=asus-rc.service
''')
text = (r / 'units/asus-rc.service').read_text()
text = text.replace('After=systemd-journald.service tmp.mount var.mount run.mount',
    'After=systemd-journald.service tmp.mount var.mount run.mount tmp-mnt.mount data.mount jffs.mount usr-local.mount tmp-mnt-JFFS.mount')
text = text.replace('RequiresMountsFor=/tmp /var /run', 'RequiresMountsFor=/tmp /var /run /tmp/mnt')
text = text.replace('Before=shutdown.target', 'Before=shutdown.target\nFailureAction=reboot')
text = text.replace('Restart=no', 'Restart=no\nDelegate=yes\nTasksMax=infinity\nTasksAccounting=no\nMemoryAccounting=no')
text = text.replace('StandardOutput=journal', 'StandardOutput=journal+console').replace('StandardError=journal', 'StandardError=journal+console')
(units / 'asus-rc.service').write_text(text)
(units / 'leon-local-ready.service').write_text('''[Unit]
Description=Wait for the existing USB local-software mount
DefaultDependencies=no
Requires=asus-rc.service
After=asus-rc.service
Conflicts=shutdown.target
Before=shutdown.target
[Service]
Type=oneshot
ExecStart=/usr/libexec/leon-local-ready
TimeoutStartSec=130
RemainAfterExit=yes
StandardOutput=journal+console
StandardError=journal+console
''')
# bcm_boot_launcher still executes its original hardware scripts in order.
# systemd owns these already mounted RAM filesystems and final global unmount.
p = root / 'rom/etc/init.d/mount-fs.sh'; before = p.read_text(); after = before
after = after.replace('\t\t/bin/mount -a', '\t\t[ -d /run/systemd/system ] || /bin/mount -a')
after = after.replace('\t\tmount -t devpts devpts /dev/pts', '\t\t[ -d /run/systemd/system ] || mount -t devpts devpts /dev/pts')
after = after.replace('\t\t/bin/umount -a -l', '\t\t[ -d /run/systemd/system ] || /bin/umount -a -l')
assert after != before; p.write_text(after)
(r / 'patches/bsp-mount-systemd.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
    fromfile='a/rom/etc/init.d/mount-fs.sh', tofile='b/rom/etc/init.d/mount-fs.sh')))
for p in base.rglob('*'):
    if p.is_dir() and not p.is_symlink() and (root / p.relative_to(base)).is_dir():
        shutil.copystat(p, root / p.relative_to(base), follow_symlinks=False)
before = inventory(base); after = inventory(root)
modules = [name for name in before if name.endswith('.ko')]
assert len(modules) == 182 and all(before[name] == after[name] for name in modules)
assert not before.keys() - after.keys()
assert not any('leon-lab' in name or 'rc-probe' in name or 'notify-probe' in name for name in after)
report = {'kernel_changed': False, 'modules_unchanged': len(modules),
    'changed': sorted(name for name in before if before[name] != after[name]),
    'added': sorted(after.keys() - before.keys()), 'real_init_sha256': sha(root / 'usr/sbin/init'),
    'real_rc_sha256': sha(root / 'usr/sbin/rc'), 'no_lab_units_or_probes': True,
    'metadata_guard': 'ARMEL guard is set only by broker for the actual rc child',
    'trial_timeout_seconds': 900, 'firmware_commit_automatic': False}
(r / 'evidence/production-staging.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k:v for k,v in report.items() if k != 'added'}, indent=2))
