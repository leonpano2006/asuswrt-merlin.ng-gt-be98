#!/usr/bin/env python3
"""glibc test-wrapper adapter: apply env assignments before launching QEMU."""
import os
import re
import sys

args = sys.argv[1:]
environment = dict(os.environ)
if args and args[0] == 'env':
    args.pop(0)
    if args and args[0] == '-i':
        args.pop(0)
        environment = {}
    while args and re.match(r'^[A-Za-z_][A-Za-z_0-9]*=', args[0]):
        key, value = args.pop(0).split('=', 1)
        environment[key] = value
if not args:
    raise SystemExit('missing guest command')
os.execvpe('qemu-aarch64', ['qemu-aarch64', '-cpu', 'cortex-a53', *args], environment)
