#!/usr/bin/env python3
"""Build the trial init/guard and Docker helper with the separately published SDKs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm32-sdk', required=True, type=Path)
    p.add_argument('--arm64-sdk', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    compilers = {
        'arm32': a.arm32_sdk.resolve() / 'bin/arm-buildroot-linux-gnueabi-gcc',
        'arm64': a.arm64_sdk.resolve() / 'bin/aarch64-buildroot-linux-gnu-gcc',
    }
    for arch, cc in compilers.items():
        if not cc.is_file():
            p.error('missing ' + str(cc))
        version = subprocess.check_output([str(cc), '-dumpfullversion'], text=True).strip()
        machine = subprocess.check_output([str(cc), '-dumpmachine'], text=True).strip()
        expected = 'arm-buildroot-linux-gnueabi' if arch == 'arm32' else 'aarch64-buildroot-linux-gnu'
        if version != '10.3.0' or machine != expected:
            p.error('use the pinned v2021.02.4-1 SDKs from kernel/dependencies.json')
    a.output.mkdir(parents=True, exist_ok=False)
    jobs = [
        ('arm32', root / 'trial/diag-init-fixed.c', 'init', []),
        ('arm32', root / 'trial/bootguard-fixed.c', 'leon-trial-bootguard.so', ['-fPIC', '-shared', '-ldl']),
        ('arm64', root / 'docker/docker-root-view.c', 'docker-root-view', []),
    ]
    files = []
    for arch, source, name, flags in jobs:
        dest = a.output / name
        command = [str(compilers[arch]), '-O2', '-Wall', '-Wextra', str(source), '-o', str(dest), *flags]
        subprocess.run(command, check=True)
        files.append({'name': name, 'architecture': arch,
                      'sha256': hashlib.sha256(dest.read_bytes()).hexdigest(),
                      'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()})
    (a.output / 'manifest.json').write_text(json.dumps(files, indent=2) + '\n')
    print(json.dumps(files, indent=2))


if __name__ == '__main__':
    main()
