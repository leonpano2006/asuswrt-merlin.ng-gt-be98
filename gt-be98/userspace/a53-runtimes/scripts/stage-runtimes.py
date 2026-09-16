#!/usr/bin/env python3
"""Stage stripped runtimes, separate debug files, Build IDs and ABI evidence."""
import json
import os
from pathlib import Path
import shutil
import subprocess
from elftools.elf.elffile import ELFFile
from common import elf_info, sha

root = Path(__file__).resolve().parents[1]
configs = json.loads((root / 'configs/build-targets.json').read_text())
baseline = root.parent / 'libgcc-runtime-20260916/rootfs'
runtime = root / 'packages/runtime'
debug = root / 'packages/debug'
assert not runtime.exists() and not debug.exists()
runtime.mkdir(parents=True)
debug.mkdir()
rows = []

def notes(path):
    with path.open('rb') as f:
        elf = ELFFile(f)
        build_id = [n['n_desc'] for s in elf.iter_sections() if s.header.sh_type == 'SHT_NOTE'
                    for n in s.iter_notes() if n['n_type'] == 'NT_GNU_BUILD_ID']
        assert len(build_id) == 1 and len(build_id[0]) == 40, path
        flags = elf.get_section_by_name('.GCC.command.line')
        flags = sorted(set(flags.data().decode().strip('\0').split('\0'))) if flags else []
        return build_id[0], flags

def stage(abi, component, source, relative, old_relative=None):
    source = source.resolve(strict=True)
    cfg = configs[abi]
    env = dict(os.environ)
    if cfg['host_library_dir']:
        env['LD_LIBRARY_PATH'] = cfg['host_library_dir']
    before = elf_info(source)
    bid, switches = notes(source)
    assert switches and all('-mcpu=cortex-a53' in s for s in switches), (component, switches)
    dest = runtime / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest)
    dest.chmod(0o755)
    symbols = debug / (abi + '-' + component + '.debug')
    subprocess.run([cfg['tools'] + 'objcopy', '--only-keep-debug', str(source), str(symbols)], env=env, check=True)
    subprocess.run([cfg['tools'] + 'strip', '--strip-unneeded', str(dest)], env=env, check=True)
    after = elf_info(dest)
    assert before == after and notes(dest) == (bid, switches)
    previous_path = baseline / (old_relative or relative)
    previous = elf_info(previous_path) if previous_path.exists() else None
    if previous:
        for key in ('class', 'machine', 'float_abi_flags', 'soname'):
            assert before[key] == previous[key], (component, key)
        missing = set(previous['exports']) - set(before['exports'])
        changes = {s: [v, before['exports'].get(s)] for s,v in previous['exports'].items()
                   if before['exports'].get(s) != v}
        (root / 'evidence' / (abi + '-' + component + '-abi.json')).write_text(
            json.dumps(dict(missing=sorted(missing), changes=changes), indent=2) + '\n')
        if abi == 'armel' and component == 'libstdcxx':
            # GCC 10's vendor library leaked 11 inline/template instantiations.
            # Keep the exact reviewed delta explicit; never silently loosen the
            # ABI gate for another symbol, object-size or visibility change.
            policy = json.loads((root / 'configs/armel-libstdcxx-abi-delta.json').read_text())
            assert sha(previous_path) == policy['baseline_sha256']
            assert missing == set(policy['missing_inline_exports'])
            for symbol in missing:
                assert previous['exports'][symbol]['binding'] == 'STB_WEAK'
                assert previous['exports'][symbol]['type'] == 'FUNCTION'
            expected = set(missing) | set(policy['binding_changes']) | set(policy['default_version_changes'])
            assert set(changes) == expected
            for symbol, (old, new) in changes.items():
                if symbol in missing:
                    continue
                allowed = dict(old)
                if symbol in policy['binding_changes']:
                    assert [old['binding'], new['binding']] == policy['binding_changes'][symbol]
                    allowed['binding'] = new['binding']
                if symbol in policy['default_version_changes']:
                    assert [old['hidden_version'], new['hidden_version']] == policy['default_version_changes'][symbol]
                    allowed['hidden_version'] = new['hidden_version']
                    # The old version remains callable; a newer default exists.
                    name = symbol.split('@')[0]
                    assert any(s.startswith(name + '@') and not v['hidden_version']
                               for s,v in before['exports'].items())
                assert allowed == new, symbol
            # Scan both ELF references and literal dlsym names, excluding only
            # the provider itself. This must be repeated for each new baseline.
            for path in baseline.rglob('*'):
                if path.is_symlink() or not path.is_file() or path == previous_path:
                    continue
                data = path.read_bytes()
                if data[:4] == b'\x7fELF' and (data[4] != 1 or
                        int.from_bytes(data[36:40], 'little') & 0x600 == 0x400):
                    continue  # A different ABI cannot consume this provider.
                assert not any(s.split('@')[0].encode() in data for s in missing), path
        else:
            assert not missing and not changes, (abi, component, len(missing), len(changes))
    rows.append(dict(abi=abi, component=component, path=relative,
                     soname=after['soname'][0], exports=len(after['exports']),
                     previous_exports=len(previous['exports']) if previous else None,
                     previous_path=str(previous_path.relative_to(baseline)) if previous else None,
                     previous_sha256=sha(previous_path) if previous else None,
                     source=str(source.relative_to(root)), unstripped_sha256=sha(source),
                     sha256=sha(dest), bytes=dest.stat().st_size, build_id_sha1=bid,
                     debug_path=str(symbols.relative_to(root)), debug_sha256=sha(symbols),
                     compiler=cfg['compiler_version'], target_flags=cfg['flags'],
                     recorded_compiler_switches=switches, glibc=cfg['glibc']))
    print('STAGED', abi, component, 'BuildID[sha1]=' + bid, flush=True)

for abi, cfg in configs.items():
    triplet = cfg['triplet']
    obj = root / 'builds' / abi / 'gcc-runtime' / triplet
    libdir = 'usr/lib/' + triplet + '/'
    stage(abi, 'libgcc', obj / 'libgcc/libgcc_s.so.1', libdir + 'libgcc_s.so.1')
    std = (obj / 'libstdc++-v3/src/.libs/libstdc++.so.6').resolve(strict=True)
    stage(abi, 'libstdcxx', std, libdir + std.name, libdir + 'libstdc++.so.6')
    (runtime / libdir / 'libstdc++.so.6').symlink_to(std.name)

c = json.loads((root / 'evidence/c-libraries-build.json').read_text())
for name, cfg in c['components'].items():
    stage('armel', name, root / cfg['artifact'], 'usr/lib/arm-linux-gnueabi/' + cfg['installed'])
assert len(rows) == 10
(root / 'packages/runtime-manifest.json').write_text(json.dumps(rows, indent=2) + '\n')
print('All 10 runtimes staged; explicit ARMEL libstdc++ legacy export delta reviewed; CPU flags and Build IDs retained.')
