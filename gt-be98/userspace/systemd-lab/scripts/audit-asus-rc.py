#!/usr/bin/env python3
"""Record the installed ASUS notification boundary without running vendor code."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
from elftools.elf.elffile import ELFFile

r = Path(__file__).resolve().parents[1]
w = r.parent
root = w / 'rootfs-no-adsl-20260916/build/unpacked-rootfs'
shared = root / 'usr/lib/arm-linux-gnueabi/libshared.so'
digest = hashlib.sha256(shared.read_bytes()).hexdigest()
assert digest == '4e8298baebb5fcfbe46566bc4fb544b90bfe9e4abb2cb039042d1116b0b747eb'
toolchain = w / 'armel-multiarch-20260915/toolchain'
env = dict(os.environ, LD_LIBRARY_PATH=str(toolchain / 'usr/lib/aarch64-linux-gnu'))
command = [str(toolchain / 'usr/bin/arm-linux-gnueabi-objdump'), '-d',
           '--start-address=0x44df4', '--stop-address=0x45128', str(shared)]
text = subprocess.check_output(command, env=env, text=True)
assert '45018:' in text and 'mov\tr1, #10' in text and 'mov\tr0, #1' in text and '<kill@plt>' in text
(r / 'evidence/libshared-notify-disassembly.txt').write_text(text)
consumers = []
for directory, dirs, files in os.walk(root, followlinks=False):
    for name in files:
        p = Path(directory) / name
        if not stat.S_ISREG(p.lstat().st_mode): continue
        with p.open('rb') as f:
            if f.read(4) != b'\x7fELF': continue
            f.seek(0)
            e = ELFFile(f)
            symbols = e.get_section_by_name('.dynsym')
            if not symbols: continue
            imports = sorted({s.name for s in symbols.iter_symbols()
                if s['st_shndx'] == 'SHN_UNDEF' and s.name.startswith('notify_rc')})
            if imports: consumers.append({'path': str(p.relative_to(root)), 'imports': imports})
report = {'libshared_sha256': digest, 'disassembly_command': command,
    'notify_internal_address': '0x44df4', 'kill_call_address': '0x45020',
    'preceding_arm_instructions': ['mov r1, #10', 'mov r0, #1'],
    'meaning': 'Installed ARMEL libshared notification code calls kill(1, SIGUSR1).',
    'dynamic_consumers': consumers, 'consumer_count': len(consumers),
    'source_search_scope': 'Archived release/src/router/shared C files have declarations, no notify_rc implementation.',
    'limitations': 'Import scan does not enumerate direct kill/syscall calls or runtime dlsym users.',
    'next_work': 'Explicit ASUS manager identity, notification endpoint and shutdown contract; do not globally falsify getpid().'}
(r / 'evidence/asus-rc-boundary.json').write_text(json.dumps(report, indent=2) + '\n')
print('ASUS_NOTIFICATION_CONSUMERS', len(consumers), flush=True)
