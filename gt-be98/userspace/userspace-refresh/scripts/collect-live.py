#!/usr/bin/env python3
"""Collect only versions and hashes over an already authorized SSH control socket."""
import datetime
import argparse
import json
from pathlib import Path
import shlex
import subprocess

r = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--router', required=True)
parser.add_argument('--control-socket', required=True)
args = parser.parse_args()
commands = {
    'kernel': ['uname', '-r'],
    'zstd': ['/usr/bin/zstd', '-V'], 'bash': ['/usr/bin/bash', '--version'],
    'nano': ['/usr/bin/nano', '--version'], 'htop': ['/usr/bin/htop', '--version'],
    'dropbear': ['/usr/bin/dropbearmulti', 'dropbear', '-V'],
    'less': ['/usr/bin/less', '--version'], 'coreutils': ['/usr/gnu/bin/coreutils', '--version'],
    'findutils': ['/usr/gnu/bin/find', '--version'], 'jq': ['/usr/gnu/bin/jq', '--version'],
    'sqlite': ['/usr/gnu/bin/sqlite3', '--version'], 'socat': ['/usr/gnu/bin/socat', '-V'],
    'util-linux': ['/usr/gnu/bin/mount', '--version'], 'btrfs-progs': ['/usr/sbin/btrfs', '--version'],
    'xfsprogs': ['/usr/sbin/mkfs.xfs', '-V'], 'dnsmasq64': ['/usr/sbin/dnsmasq64', '--version'],
    'openssl': ['/usr/sbin/openssl', 'version'], 'openvpn': ['/usr/sbin/openvpn', '--version'],
    'curl': ['/usr/sbin/curl', '--version'], 'docker': ['/usr/local/bin/docker', '--version'],
    'iperf': ['/usr/bin/iperf3', '--version'], 'systemd': ['/usr/bin/systemctl', '--version'],
    'zstd_and_tls_hashes': ['sha256sum', '/usr/bin/zstd', '/usr/lib/aarch64-linux-gnu/libzstd.so.1.5.7',
                          '/usr/sbin/openssl', '/usr/lib/arm-linux-gnueabi/libcrypto.so.1.1',
                          '/usr/lib/arm-linux-gnueabi/libcrypto.so.3'],
}
script = ''.join('printf "\\nAUDIT_ITEM:%s\\n" ' + shlex.quote(name) + '\n' +
                 shlex.join(argv) + ' 2>&1 | head -6\n' for name, argv in commands.items())
p = subprocess.run(['ssh', '-S', args.control_socket, '-o', 'BatchMode=yes',
                    '-o', 'ConnectTimeout=10', args.router, 'sh -s'],
                   input=script, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
assert p.returncode == 0, p.stderr
rows = {}
for part in p.stdout.split('AUDIT_ITEM:')[1:]:
    name, text = part.split('\n', 1); rows[name] = text.strip()
record = {'time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'router': args.router, 'commands': commands, 'results': rows,
          'router_modified': False}
(r / 'evidence/live-versions.json').write_text(json.dumps(record, indent=2) + '\n')
for name, result in rows.items():
    print(name + ': ' + result.split('\n')[0])
