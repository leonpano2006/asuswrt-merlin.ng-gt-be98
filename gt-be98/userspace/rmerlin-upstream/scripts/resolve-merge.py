#!/usr/bin/env python3
"""Explicit, reproducible resolutions for the seven reviewed merge conflicts."""
from pathlib import Path
import difflib
import hashlib
import json
import re

r = Path(__file__).resolve().parents[1]
root = r / 'conflicts'
dest = r / 'resolved'
dest.mkdir(exist_ok=True)
pattern = re.compile(r'^<<<<<<<[^\n]*\n(.*?)^=======\n(.*?)^>>>>>>>[^\n]*\n', re.M | re.S)
records = []
def save(name, text, reason):
    assert not re.search(r'^(<<<<<<< |=======\s*$|>>>>>>> )', text, re.M), name
    p = dest / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    old = (root / 'upstream' / name).read_text()
    records.append({'path': name, 'reason': reason,
                    'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
    return ''.join(difflib.unified_diff(old.splitlines(True), text.splitlines(True),
                   fromfile='a/' + name, tofile='b/' + name))
patch = ''
name = 'Changelog-3006.txt'
text = (root / 'upstream' / name).read_text()
old = (root / 'ours' / name).read_text()
legacy = old.split('=================================\n\n', 1)[1].split('3006.102.7_2 (', 1)[0]
text = text.replace('3006.102.7_2 (24-Mar-2026)', legacy + '3006.102.7_2 (24-Mar-2026)', 1)
patch += save(name, text, 'Use current upstream release notes and retain the historical gnuton entry.')

name = 'release/src/router/openvpn/ChangeLog'
patch += save(name, (root / 'upstream' / name).read_text(), 'Use the upstream OpenVPN 2.7.7 package changelog.')

name = 'release/src-rt/version.conf'
text = (root / 'upstream' / name).read_text()
assert text.count('EXTENDNO=beta1\n') == 1
text = text.replace('EXTENDNO=beta1\n', 'EXTENDNO=beta1-leon1\n')
patch += save(name, text, 'Identify the integration as a Leon build based on 102.9 beta1.')

name = 'release/src/router/Makefile'
text = (root / 'merged' / name).read_text()
blocks = list(pattern.finditer(text))
assert len(blocks) == 1 and 'touch aclocal.m4' in blocks[0][1]
text = pattern.sub(lambda m: m[1], text)
patch += save(name, text, 'Retain the more complete wget autotools timestamp workaround and all automatic merges.')

name = 'release/src-rt-5.04behnd.4916/kernel/linux-4.19/config_base.6a.6813'
text = (root / 'merged' / name).read_text()
blocks = list(pattern.finditer(text))
assert len(blocks) == 1
assert all(line.startswith('# CONFIG_') and line.endswith(' is not set')
           for line in (blocks[0][1] + blocks[0][2]).splitlines())
text = pattern.sub(lambda m: m[1] + m[2], text)
patch += save(name, text, 'Preserve local kernel configuration and both sets of disabled pressure sensor options.')

name = 'release/src/router/www/js/asus.js'
text = (root / 'merged' / name).read_text()
blocks = list(pattern.finditer(text))
assert len(blocks) == 5
replacements = [
    '\n        return nBandArray[dwb_band] && dwb_mode === "1" ? "1" : "0";\n',
    '        if (object.dwbMode === "1") {\n            (nBandArray || []).forEach((element) => {\n',
    '    let { wlnband_list } = nvram;\n    let nBandArray = (wlnband_list || "").split("&#60");\n',
    '                    let dwbChannel = objectDeepCopy(aMesh.channel[wlIfIndex] || {});\n',
    '                        if (Array.isArray(chanspec)) {\n'
    '                            channel = channel.concat(chanspec.filter((element) => element !== "0"));\n',
]
for match, replacement in reversed(list(zip(blocks, replacements))):
    text = text[:match.start()] + replacement + text[match.end():]
patch += save(name, text, 'Combine GT-BE98 DWB/channel handling with upstream missing-value guards.')

name = 'release/src/router/www/QoS_EZQoS.asp'
text = (root / 'upstream' / name).read_text()
start = text.index('} else if (value == 1) {\t\t//Adaptive QoS')
end = text.index('} else if (value == 2) {', start)
part = text[start:end]
needle = "document.getElementById('bandwidth_setting_tr').style.display = \"\";"
assert part.count(needle) == 1
part = part.replace(needle, "document.getElementById('bandwidth_setting_tr').style.display = "
                    "(based_modelid === 'GT-BE98') ? \"none\" : \"\";")
needle = 'if(document.getElementById("auto").checked){'
assert part.count(needle) == 1
part = part.replace(needle, 'if(based_modelid === "GT-BE98" || document.getElementById("auto").checked){')
text = text[:start] + part + text[end:]
patch += save(name, text, 'Use the new QoS/HW AQM page; preserve inherited Adaptive QoS rate-field behavior only for GT-BE98.')

(r / 'patches/reviewed-merge-resolutions.patch').write_text(patch)
(r / 'evidence/merge-resolutions.json').write_text(json.dumps(records, indent=2) + '\n')
print('RESOLVED', len(records), 'files')
