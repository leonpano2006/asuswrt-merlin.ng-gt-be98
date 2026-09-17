#!/usr/bin/env python3
"""Read-only ASUS GETINFO probe to the user's router; never sends SET commands."""
from pathlib import Path
import hashlib
import json
import socket
import struct
import time

router = '192.168.100.10'
# shared/iboxcom.h and infosvr/packet.c: service 12, command 21, GETINFO 31.
packet = struct.pack('<BBHI', 12, 21, 31, 0).ljust(512, b'\0')
record = None
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(('', 0))
    for attempt in range(3):
        sock.sendto(packet, (router, 9999))
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            sock.settimeout(max(.05, deadline - time.monotonic()))
            try:
                data, peer = sock.recvfrom(4096)
            except TimeoutError:
                break
            if peer[0] != router or len(data) < 248:
                continue
            if struct.unpack_from('<BBH', data) != (12, 22, 31):
                continue
            product = data[200:232].split(b'\0')[0].decode('ascii')
            assert product == 'GT-BE98', product
            record = {'passed': True, 'opcode': 31, 'product': product,
                      'bytes': len(data), 'response_sha256': hashlib.sha256(data).hexdigest(),
                      'source_port': peer[1], 'attempts': attempt + 1}
            break
        if record:
            break
assert record, 'No valid GT-BE98 GETINFO response'
out = Path(__file__).resolve().parents[1] / 'evidence/discovery.json'
out.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
