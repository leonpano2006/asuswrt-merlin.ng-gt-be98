#!/usr/bin/env python3
"""Build only the manager and tools needed by the offline PID 1 experiment."""
import json
import os
from pathlib import Path
import subprocess

r = Path(__file__).resolve().parents[1]
w = r.parent
source = next((r / 'sources').glob('systemd-*/'))
sdk = r / 'sdk'
build = r / 'build/systemd'
config = r / 'configs/aarch64-sysroot.ini'
config.write_text(f'''[binaries]
c = '{r / 'build/cc'}'
ar = '/usr/bin/aarch64-linux-gnu-ar'
strip = '/usr/bin/aarch64-linux-gnu-strip'
pkg-config = '/usr/bin/pkg-config'
exe_wrapper = '{r / 'build/run-target'}'

[host_machine]
system = 'linux'
cpu_family = 'aarch64'
cpu = 'cortex-a53'
endian = 'little'

[properties]
sys_root = '{sdk}'
pkg_config_libdir = ['{sdk / 'usr/lib/aarch64-linux-gnu/pkgconfig'}']
needs_exe_wrapper = true

[built-in options]
c_args = ['-Oz', '-g', '-frecord-gcc-switches']
c_link_args = ['-Oz', '-frecord-gcc-switches', '-Wl,--build-id=sha1']
''')
disabled = ['initrd', 'nscd', 'utmp', 'hibernate', 'ldconfig', 'resolve', 'efi', 'tpm',
    'binfmt', 'coredump', 'pstore', 'oomd', 'logind', 'hostnamed', 'localed', 'machined',
    'portabled', 'sysext', 'userdb', 'networkd', 'timedated', 'timesyncd', 'create-log-dirs',
    'nss-myhostname', 'nss-systemd', 'firstboot', 'randomseed', 'backlight', 'vconsole',
    'quotacheck', 'storagetm', 'hwdb', 'rfkill', 'xdg-autostart', 'translations', 'smack',
    'ima', 'idn', 'kernel-install', 'analyze', 'default-kill-user-processes', 'mountfsd', 'nsresourced', 'importd']
options = ['--prefix=/usr', '--libdir=lib/aarch64-linux-gnu', '--sysconfdir=/etc', '--localstatedir=/var',
    '--buildtype=minsize', '-Dauto_features=disabled', '-Dmode=release', '-Dtests=false',
    '-Db_lto=true', '-Dsplit-usr=false', '-Dsplit-bin=true',
    '-Dc_args=-Oz -g -frecord-gcc-switches',
    '-Dc_link_args=-Oz -frecord-gcc-switches -Wl,--build-id=sha1',
    '-Dversion-tag=257.13-gt-be98', '-Dsysusers=true', '-Dtmpfiles=true',
    '-Dsysvinit-path=', '-Dsysvrcnd-path=', '-Drootprefix=/usr', '-Dman=disabled', '-Dhtml=disabled',
    '-Dlink-executor-shared=true', '-Dlink-systemctl-shared=true', '-Dlink-journalctl-shared=true',
    '-Dnobody-user=nobody', '-Dnobody-group=nogroup', '-Dmount-path=/usr/gnu/bin/mount',
    '-Dumount-path=/usr/gnu/bin/umount'] + ['-D' + name + '=false' for name in disabled]
env = dict(os.environ, PATH=str(w / 'systemd-lab-20260916/host/bin') + ':' + os.environ['PATH'], LC_ALL='C')
env.pop('LD_LIBRARY_PATH', None)
env.pop('PKG_CONFIG_PATH', None)
setup = ['meson', 'setup', str(build), str(source), '--cross-file', str(config)] + options
if (build / 'build.ninja').exists():
    setup.append('--reconfigure')
targets = ['systemd', 'systemd-executor', 'systemd-shutdown', 'systemctl',
           'systemd-journald', 'journalctl', 'systemd-notify', 'systemd-run']
commands = [setup, ['ninja', '-C', str(build), '-j4'] + targets]
(r / 'evidence/systemd-commands.json').write_text(json.dumps({
    'commands': commands, 'notes': 'Native AArch64 compiler; Meson cross-file isolates a distinct router glibc sysroot and loader.'}, indent=2) + '\n')
for name, cmd in zip(('systemd-configure', 'systemd-build'), commands):
    print(name, flush=True)
    with (r / 'evidence' / (name + '.log')).open('w') as log:
        p = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
    if p.returncode:
        print((r / 'evidence' / (name + '.log')).read_text()[-7500:], flush=True)
        raise SystemExit(p.returncode)
    if name == 'systemd-configure':
        actual = {x['name']: x['value'] for x in json.loads((build / 'meson-info/intro-buildoptions.json').read_text())}
        assert '-Oz' in actual['c_args'] and '-Oz' in actual['c_link_args'], 'Meson reused cached compiler options; use a fresh build directory'
print('SYSTEMD_BUILT', flush=True)
