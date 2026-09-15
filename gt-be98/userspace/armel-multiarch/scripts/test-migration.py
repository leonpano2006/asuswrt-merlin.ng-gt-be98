#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('migration', Path(__file__).with_name('migrate-rootfs.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def elf(flags=0x5000200):
    ident = b'\x7fELF\x01\x01\x01' + bytes(9)
    return ident + struct.pack('<HHIIIIIHHHHHH', 3, 40, 1, 0, 0, 0, flags, 52, 32, 0, 40, 0, 0)

class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.src = self.base/'source'
        (self.src/'usr/lib').mkdir(parents=True)
        (self.src/'rom/etc').mkdir(parents=True)
        (self.src/'rom/etc/ld.so.conf').write_text('/lib\n/usr/lib\n')
        (self.src/'lib').symlink_to('usr/lib')
        for name in m.PRIVATE:
            d = self.src/'usr/lib'/name
            d.mkdir()
            (d/'plugin.so').write_bytes(elf())
        (self.src/'usr/lib/ld-linux.so.3').write_bytes(elf())
        (self.src/'usr/lib/libsample.so.1').write_bytes(elf())
        (self.src/'usr/lib/libsample.so').symlink_to('libsample.so.1')
        (self.src/'usr/lib/ipsec/relative.so').symlink_to('../libsample.so.1')
        (self.src/'usr/lib/absolute.so').symlink_to('/lib/libsample.so.1')
        self.out = self.base/'result'

    def test_loader_and_plugin_paths_resolve_to_same_content(self):
        report = m.migrate(self.src, self.out)
        for name in ('/lib/ld-linux.so.3', '/lib/libsample.so', '/usr/lib/ipsec/relative.so', '/lib/absolute.so'):
            self.assertEqual(m.resolve(self.out, name).read_bytes(), elf())
        self.assertEqual((self.out/'usr/lib/ld-linux.so.3').readlink(), Path('arm-linux-gnueabi/ld-linux.so.3'))
        self.assertTrue((self.out/'usr/lib/arm-linux-gnueabi/ipsec/relative.so').is_symlink())
        self.assertEqual(report['flat_armel_elf_files_remaining'], 0)
        self.assertEqual((self.src/'rom/etc/ld.so.conf').read_text(), '/lib\n/usr/lib\n')

    def test_mixed_plugin_abi_is_rejected_before_copy(self):
        (self.src/'usr/lib/xtables/plugin.so').write_bytes(elf(0x5000400))
        with self.assertRaisesRegex(ValueError, 'mixed or unknown'):
            m.migrate(self.src, self.out)
        self.assertFalse(self.out.exists())

    def test_existing_destination_is_rejected(self):
        (self.src/m.ARMEL).mkdir()
        with self.assertRaisesRegex(ValueError, 'destination already exists'):
            m.migrate(self.src, self.out)

    def test_output_cannot_be_inside_input(self):
        with self.assertRaisesRegex(ValueError, 'separate tree'):
            m.migrate(self.src, self.src/'nested')

    def test_absolute_symlink_never_resolves_on_host(self):
        self.assertEqual(m.resolve(self.src, '/lib/absolute.so'), self.src/'usr/lib/libsample.so.1')

if __name__ == '__main__':
    unittest.main()
