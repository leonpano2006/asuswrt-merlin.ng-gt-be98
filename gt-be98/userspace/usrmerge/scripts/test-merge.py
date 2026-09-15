#!/usr/bin/env python3
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

script = Path(__file__).with_name('merge-rootfs.py')
spec = importlib.util.spec_from_file_location('merge', script)
merge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(merge)

class MergeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / 'source'
        for name in ['bin', 'sbin', 'lib', 'usr/bin', 'usr/sbin', 'usr/lib', 'rom/etc']:
            (self.source / name).mkdir(parents=True, exist_ok=True)
        for name, data in [('lib/libresolv.so.2', b'current'), ('usr/lib/libresolv.so.2', b'old'), ('usr/bin/bash', b'shell'), ('usr/lib/libexpat.so.1', b'expat')]:
            (self.source / name).write_bytes(data)
        (self.source / 'bin/bash').symlink_to('/usr/bin/bash')
        (self.source / 'lib/libexpat.so').symlink_to('../usr/lib/libexpat.so.1')
        (self.source / 'usr/lib/libresolv.so.2').chmod(0o755)
        (self.source / 'lib/libresolv.so.2').chmod(0o640)
        self.policy = self.base / 'policy.json'
        self.policy.write_text(json.dumps({n: merge.sha(self.source / n) for n in ['lib/libresolv.so.2', 'usr/lib/libresolv.so.2']}))
        self.out = self.base / 'output'
        self.command = ['python3', str(script), '--source', str(self.source), '--output', str(self.out), '--resolv-policy', str(self.policy), '--report', str(self.base / 'report.json')]

    def test_merge_preserves_aliases_and_lib_metadata(self):
        subprocess.run(self.command, check=True, capture_output=True)
        for name in ['bin', 'sbin', 'lib']:
            self.assertEqual((self.out / name).readlink().as_posix(), 'usr/' + name)
        self.assertEqual(merge.resolve(self.out, '/bin/bash').read_bytes(), b'shell')
        self.assertEqual(merge.resolve(self.out, '/lib/libexpat.so').read_bytes(), b'expat')
        self.assertEqual((self.out / 'usr/lib/libexpat.so').readlink().as_posix(), 'libexpat.so.1')
        self.assertEqual((self.out / 'usr/lib/libresolv.so.2').stat().st_mode & 0o777, 0o640)
        self.assertEqual((self.source / 'usr/lib/libresolv.so.2').read_bytes(), b'old')

    def test_unknown_collision_fails_before_copy(self):
        (self.source / 'bin/tool').write_bytes(b'first')
        (self.source / 'usr/bin/tool').write_bytes(b'second')
        result = subprocess.run(self.command, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.out.exists())

    def test_unpinned_resolver_fails_before_copy(self):
        (self.source / 'lib/libresolv.so.2').write_bytes(b'unreviewed')
        self.assertNotEqual(subprocess.run(self.command, capture_output=True).returncode, 0)
        self.assertFalse(self.out.exists())

    def test_existing_output_is_never_replaced(self):
        self.out.mkdir()
        marker = self.out / 'keep'
        marker.write_bytes(b'keep')
        self.assertNotEqual(subprocess.run(self.command, capture_output=True).returncode, 0)
        self.assertEqual(marker.read_bytes(), b'keep')

    def test_absolute_link_stays_within_image(self):
        (self.source / 'lib/host').symlink_to('/etc/passwd')
        self.assertEqual(merge.resolve(self.source, '/lib/host'), self.source / 'etc/passwd')
        self.assertFalse(merge.resolve(self.source, '/lib/host').exists())

    def test_loop_is_rejected(self):
        (self.source / 'lib/loop').symlink_to('loop')
        with self.assertRaises(RuntimeError):
            merge.resolve(self.source, '/lib/loop')

if __name__ == '__main__':
    unittest.main()
