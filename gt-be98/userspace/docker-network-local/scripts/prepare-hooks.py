#!/usr/bin/env python3
"""Generate hook updates from the inspected router backup, preserving its code."""
import argparse
import hashlib
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--before', type=Path, required=True, help='extracted backup jffs directory')
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
expected = {
    'scripts/post-mount': 'e9bbf7df905d49d4dfc5048c4fb57176e7bff1ab16fbd4401c9b28a19bbde287',
    'scripts/services-start': 'c44b36aeb8c225b5d0b6016cae50f72793c3531465dfe9ac45bfc41cee9a879b',
    'configs/profile.add': '17b9bd8aed28eb43f48b808583c9db339d59a5710b4aeceb07d8a31f0f7ea92d',
}
texts = {}
for name, sha in expected.items():
    data = (a.before / name).read_bytes()
    if hashlib.sha256(data).hexdigest() != sha:
        raise SystemExit(f'Unexpected existing hook: {name}; merge manually instead of overwriting it')
    texts[name] = data.decode()
s = texts['scripts/post-mount']
needle = '    # /root is tmpfs'
assert s.count(needle) == 1
s = s.replace(needle, '    # Restore the USB-backed local software prefix after the JFFS bind.\n    [ ! -x /jffs/scripts/local-mount ] || /jffs/scripts/local-mount >> "$LOG" 2>&1\n' + needle)
a.out.mkdir(parents=True, exist_ok=True)
(a.out / 'post-mount').write_text(s)
s = texts['scripts/services-start']
s += '\n# Idempotent fallback when USB mounted before this hook.\n[ ! -x /jffs/scripts/local-mount ] || /jffs/scripts/local-mount\n'
(a.out / 'services-start').write_text(s)
s = texts['configs/profile.add']
needle = '# hand interactive logins'
assert s.count(needle) == 1
s = s.replace(needle, '# USB local software takes precedence after the Entware profile is sourced.\nexport PATH=/usr/local/bin:/usr/local/sbin:$PATH\n\n' + needle)
(a.out / 'profile.add').write_text(s)
