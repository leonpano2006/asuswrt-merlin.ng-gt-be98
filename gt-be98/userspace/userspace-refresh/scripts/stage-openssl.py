#!/usr/bin/env python3
"""Stage an additive ARM64 overlay; preserve all pre-existing firmware paths."""
import hashlib
import json
from pathlib import Path
import shutil
import stat
import subprocess
from elftools.elf.elffile import ELFFile

r = Path(__file__).resolve().parents[1]
install = r / 'build/openssl4-install'
overlay = r / 'overlay'
parent = r.parent / 'systemd-rc-next-20260917/build/production-rootfs'
libdir = 'usr/lib/aarch64-linux-gnu'
mapping = {libdir + '/' + n: libdir + '/' + n for n in ('libcrypto.so.4', 'libssl.so.4', 'ossl-modules/legacy.so')}
mapping['usr/libexec/openssl4'] = 'usr/bin/openssl'
records = {}
for dest, src in mapping.items():
    p = overlay / dest
    assert not (parent / dest).exists() and not (parent / dest).is_symlink(), dest
    p.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(install / src, p)
    subprocess.run(['aarch64-linux-gnu-strip', '--strip-unneeded', str(p)], check=True)
    with p.open('rb') as stream:
        elf = ELFFile(stream)
        assert elf.header.e_machine == 'EM_AARCH64'
        dynamic = list(elf.get_section_by_name('.dynamic').iter_tags())
        assert not any(t.entry.d_tag in ('DT_RPATH', 'DT_RUNPATH') for t in dynamic)
        buildid = next(n['n_desc'] for n in elf.get_section_by_name('.note.gnu.build-id').iter_notes()
                       if n['n_type'] == 'NT_GNU_BUILD_ID')
        flags = elf.get_section_by_name('.GCC.command.line').data().decode().split('\0')
        assert any('-mcpu=cortex-a53+crc+crypto' in s for s in flags)
        records[dest] = {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                         'build_id_sha1': buildid, 'compiler_flags': flags,
                         'needed': [t.needed for t in dynamic if t.entry.d_tag == 'DT_NEEDED']}
config = overlay / 'usr/lib/ssl/openssl4/openssl.cnf'
assert not (parent / str(config.relative_to(overlay))).exists()
config.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(r / 'sources/openssl-4.0.2/apps/openssl.cnf', config)
records[str(config.relative_to(overlay))] = {'bytes': config.stat().st_size,
                                         'sha256': hashlib.sha256(config.read_bytes()).hexdigest()}
# An overlay must not propagate the build user's umask onto existing /usr dirs.
for directory in [overlay, *(p for p in overlay.rglob('*') if p.is_dir() and not p.is_symlink())]:
    previous = parent / directory.relative_to(overlay)
    directory.chmod(stat.S_IMODE(previous.stat().st_mode) if previous.is_dir() else 0o755)
# Development headers and unversioned linker names belong only to the SDK.
shutil.copytree(install / 'usr/include/openssl', r / 'sdk/usr/include/openssl', dirs_exist_ok=True)
for src in (install / libdir).glob('*'):
    if src.name.startswith(('libcrypto.so', 'libssl.so')):
        dst = r / 'sdk' / libdir / src.name
        if dst.exists() or dst.is_symlink(): dst.unlink()
        if src.is_symlink(): dst.symlink_to(src.readlink())
        else: shutil.copy2(src, dst)
for src in (install / libdir / 'pkgconfig').glob('*.pc'):
    shutil.copy2(src, r / 'sdk' / libdir / 'pkgconfig' / src.name)
record = {'files': records, 'bytes': sum(x['bytes'] for x in records.values()),
          'existing_production_paths_replaced': [], 'unversioned_runtime_library_links': [],
          'existing_cli_and_config_unchanged': True,
          'status': 'component_overlay_not_flashed'}
(r / 'evidence/openssl4-overlay.json').write_text(json.dumps(record, indent=2) + '\n')
print('ADDITIVE_OVERLAY_BYTES', record['bytes'])
