#!/usr/bin/env python3
"""Create a minimal runtime overlay, applying Meson's normal install-RPATH transformation."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from elftools.elf.elffile import ELFFile
from mesonbuild.scripts.depfixer import fix_rpath

r = Path(__file__).resolve().parents[1]
build = r / 'build/systemd'
stage = r / 'overlay'
stage.mkdir(exist_ok=True)
private = 'usr/lib/aarch64-linux-gnu/systemd'
mapping = {name: 'usr/lib/systemd/' + name for name in
           ('systemd', 'systemd-executor', 'systemd-shutdown', 'systemd-journald')}
mapping.update({name: 'usr/bin/' + name for name in ('systemctl', 'journalctl', 'systemd-notify', 'systemd-run')})
mapping.update({'src/core/libsystemd-core-257.so': private + '/libsystemd-core-257.so',
                'src/shared/libsystemd-shared-257.so': private + '/libsystemd-shared-257.so'})
records = {}
object_flags = {}
for obj in build.rglob('*.c.o'):
    with obj.open('rb') as f:
        flags = ELFFile(f).get_section_by_name('.GCC.command.line')
        switches = flags.data().decode().split('\0') if flags else []
    assert any('-mcpu=cortex-a53+crc+crypto' in x for x in switches), str(obj)
    object_flags[str(obj.relative_to(build))] = {
        'sha256': hashlib.sha256(obj.read_bytes()).hexdigest(), 'gcc_switches': switches}
assert object_flags
(r / 'evidence/systemd-object-flags.json').write_text(json.dumps(object_flags, indent=2) + '\n')
for src, dest in mapping.items():
    p = stage / dest
    p.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(build / src, p)
    with p.open('rb') as f:
        elf = ELFFile(f)
        dyn = elf.get_section_by_name('.dynamic')
        paths = {part.encode() for tag in dyn.iter_tags() if tag.entry.d_tag in ('DT_RPATH', 'DT_RUNPATH')
                 for part in getattr(tag, 'runpath', getattr(tag, 'rpath', '')).split(':')}
    install_rpath = '$ORIGIN' if p.name.endswith('.so') else '/' + private
    fix_rpath(str(p), paths, install_rpath, str(p), {}, False)
    subprocess.run(['aarch64-linux-gnu-strip', '--strip-unneeded', str(p)], check=True)
    records[dest] = {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size}
lib = stage / 'usr/lib/aarch64-linux-gnu'
search = ':'.join(str(p) for p in [stage / private, lib, r / 'sdk/usr/lib/aarch64-linux-gnu', r / 'sdk/lib/aarch64-linux-gnu'])
loader = r / 'sdk/lib/ld-linux-aarch64.so.1'
for name, row in records.items():
    p = stage / name
    out = subprocess.check_output([str(loader), '--library-path', search, '--list', str(p)], text=True)
    assert '/lib/aarch64-linux-gnu' not in out.replace(str(r), '').replace('/sdk/lib/aarch64-linux-gnu', '').replace('/sdk/usr/lib/aarch64-linux-gnu', '').replace('/overlay/usr/lib/aarch64-linux-gnu', ''), out
    row['loader_dependencies'] = out.splitlines()
    with p.open('rb') as f:
        elf = ELFFile(f)
        notes = elf.get_section_by_name('.note.gnu.build-id')
        row['build_id_sha1'] = next(n['n_desc'] for n in notes.iter_notes() if n['n_type'] == 'NT_GNU_BUILD_ID')
        flags = elf.get_section_by_name('.GCC.command.line')
        row['gcc_switches'] = flags.data().decode().split('\0') if flags else []
        row['isa_evidence'] = 'systemd-object-flags.json; LTO does not retain the object command-line sections in final ELF'
version = subprocess.check_output([str(loader), '--library-path', search, str(stage / 'usr/lib/systemd/systemd'), '--version'], text=True)
(r / 'evidence/systemd-version.txt').write_text(version)
(r / 'evidence/runtime-overlay.json').write_text(json.dumps({'files': records, 'regular_files': len(records),
    'bytes': sum(x['bytes'] for x in records.values()), 'version': version, 'compiler': 'GCC 16.2.0',
    'sysroot_glibc': '2.44', 'mcpu': 'cortex-a53+crc+crypto'}, indent=2) + '\n')
print(version, flush=True)
print('OVERLAY_BYTES', sum(x['bytes'] for x in records.values()), flush=True)
