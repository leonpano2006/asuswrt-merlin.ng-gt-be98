#!/usr/bin/env python3
"""Exercise the installed pager through real SSH PTYs without restarting services."""
from pathlib import Path
import json
import pexpect
import shlex
import subprocess
import time

r = Path(__file__).resolve().parents[1]
ssh = ['ssh', '-S', '/tmp/gtbe98-systemd257-live.sock', '-o', 'BatchMode=yes',
       '-o', 'ConnectTimeout=10']
host = 'MastermixStudios@192.168.100.10'
fixture = ''.join(f'[{i:04d}] 中文分頁測試 \x1b[32m綠色\x1b[0m UNIQUE_TARGET_{i:03d}\n'
                  for i in range(1, 201))
subprocess.run(ssh + [host, 'cat > /tmp/leon-less-704-test.txt'],
               input=fixture.encode(), check=True)
tests = [
    ('direct', '/usr/bin/less -RSXMK /tmp/leon-less-704-test.txt'),
    ('systemctl', '/usr/bin/systemctl list-units --all'),
    ('journalctl', '/usr/bin/journalctl -b -n 100 --no-hostname'),
    ('systemctl-login', '/usr/bin/systemctl list-units --all'),
    ('journalctl-login', '/usr/bin/journalctl -b -n 100 --no-hostname'),
]
results = []
try:
    for label, command in tests:
        env = ('unset SYSTEMD_PAGER PAGER SYSTEMD_LESS LESS; '
               'export TERM=xterm-256color PATH=/usr/bin:/usr/sbin:/bin:/sbin '
               'LESSCHARSET=utf-8 LEON_PAGER_PROBE=less704-' + label + '; ')
        if label.endswith('-login'):
            env += 'source /etc/profile; '
        script = env + command + '; status=$?; echo LEON_PAGER_RETURN:$status'
        child = pexpect.spawn('ssh', ssh[1:] + ['-tt', host,
            '/usr/bin/bash -c ' + shlex.quote(script)], encoding='utf-8',
            codec_errors='replace', timeout=15, dimensions=(10, 100))
        with (r / 'evidence' / (label + '-tty.log')).open('w') as log:
            child.logfile = log
            try:
                child.expect(r'(lines [0-9]+-[0-9]+|\(END\))')
                inspect = ('for p in /proc/[0-9]*; do '
                    '[ "$(cat "$p/comm" 2>/dev/null)" = less ] || continue; '
                    'tr "\\0" "\\n" < "$p/environ" 2>/dev/null | '
                    'grep -qx LEON_PAGER_PROBE=less704-' + label + ' || continue; '
                    'readlink "$p/exe"; '
                    'tr "\\0" "\\n" < "$p/environ" | grep -E "^(LESS|LESSSECURE|LESSCHARSET)="; done')
                observed = subprocess.check_output(ssh + [host, inspect], text=True)
                assert '/usr/bin/less\n' in observed, observed
                child.send(' ')
                time.sleep(.15)
                if label == 'direct':
                    child.send('/UNIQUE_TARGET_19[9]\r')
                    child.expect(r'\[0199\].*UNIQUE_TARGET_199')
                    child.send('g')
                    child.expect(r'\[0001\].*UNIQUE_TARGET_001')
                child.send('q')
                child.expect('LEON_PAGER_RETURN:0')
                child.expect(pexpect.EOF)
                child.close()
                assert child.exitstatus == 0
                log.flush()
                if label == 'direct':
                    output = (r / 'evidence/direct-tty.log').read_text()
                    assert '中文分頁測試' in output and '\x1b[32m' in output
                results.append({'test': label, 'passed': True,
                                'pager_environment': observed.splitlines(),
                                'scroll_and_quit': True,
                                'utf8_color_regex_search': label == 'direct'})
            finally:
                if child.isalive():
                    child.send('q')
                    child.close(force=True)
finally:
    subprocess.run(ssh + [host, 'rm -f /tmp/leon-less-704-test.txt'], check=True)
(r / 'evidence/live-tests.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results, indent=2))
