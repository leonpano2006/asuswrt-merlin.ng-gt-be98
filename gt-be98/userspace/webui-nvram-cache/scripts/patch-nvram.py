#!/usr/bin/env python3
"""Repair one hash-pinned vendor cache getter, leaving every ABI entry intact."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

SOURCE_SHA256 = '6eb214a9e4de1269d5467c8ac5d9f3ed4fdfda535d6546ea222fba44d0e35c46'
SITE, CAVE = 0x56ac, 0x7810

def branch(source, target, opcode=0xea000000):
    delta = target - source - 8
    assert delta % 4 == 0 and -(1 << 25) <= delta < (1 << 25)
    return opcode | ((delta // 4) & 0xffffff)

def patch(source):
    assert hashlib.sha256(source).hexdigest() == SOURCE_SHA256, 'Unsupported source library'
    assert source[:7] == b'\x7fELF\x01\x01\x01'
    assert struct.unpack_from('<H', source, 18)[0] == 40, 'Expected ARM ELF'
    assert struct.unpack_from('<II', source, 52) == (1, 0), 'Expected first PT_LOAD at offset zero'
    assert struct.unpack_from('<II', source, 68) == (0x7804, 0x7804)
    assert struct.unpack_from('<II', source, 76) == (5, 0x10000), 'Expected RX segment'
    assert struct.unpack_from('<I', source, SITE)[0] == branch(SITE, 0x5064, 0xeb000000)
    words = [branch(CAVE, 0x5064, 0xeb000000), 0xe1a00006,
             branch(CAVE + 8, 0x4bc8, 0xeb000000), 0xe1a04000,
             0xe3540000, branch(CAVE + 20, 0x568c, 0x0a000000),
             branch(CAVE + 24, 0x56b0)]
    code = struct.pack('<7I', *words)
    end = CAVE + len(code)
    assert source[0x7804:end] == bytes(end - 0x7804), 'Padding is not empty'
    assert end < 0x7f30, 'Would overlap the next segment data'
    result = bytearray(source)
    struct.pack_into('<II', result, 68, end, end)
    struct.pack_into('<I', result, SITE, branch(SITE, CAVE))
    result[CAVE:end] = code
    return bytes(result), code

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    data, code = patch(args.source.read_bytes())
    with args.output.open('xb') as output:
        output.write(data)
    args.output.chmod(0o755)
    manifest = {'input_sha256': SOURCE_SHA256, 'output_sha256': hashlib.sha256(data).hexdigest(),
                'bytes': len(data), 'patch_site': hex(SITE), 'trampoline': hex(CAVE),
                'trampoline_hex': code.hex(), 'source_assembly': 'cache-get-refresh.S',
                'changes': 'Re-find the cache entry after update/removal before dereferencing it.'}
    args.output.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(manifest, indent=2))

if __name__ == '__main__':
    main()
