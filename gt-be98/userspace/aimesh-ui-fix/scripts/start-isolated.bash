#!/usr/bin/bash
set -eu
export SYSTEMD_PAGER=cat SYSTEMD_COLORS=0
hash() { sha256sum "$1" | cut -d' ' -f1; }
test "$(hash /usr/sbin/httpd)" = e1c6013f9e535cd76294a4acc814b5b985fb487e79dff60066b18d52cd8bf450
test "$(hash /tmp/leon-aimesh/httpd)" = 2035aca8e26a14b0823e340ac08e2eddeb13d494d2595bc54e0014d4ba73cd0b
test "$(hash /tmp/leon-aimesh/aimesh_topology.html)" = 3cef091a58002ec0b1928473531d8c41355219cc5c1d20f6dc8bc4152f8e7e4c
! systemctl is-active --quiet leon-aimesh-namespace-test.service
systemd-run --unit=leon-aimesh-namespace-test \
    --property=Type=simple --property=WorkingDirectory=/www --property=UMask=0077 \
    --property=RuntimeMaxSec=1800 --property=PrivateMounts=yes \
    --property=BindReadOnlyPaths=/tmp/leon-aimesh/httpd:/usr/sbin/httpd \
    --property=BindReadOnlyPaths=/tmp/leon-aimesh/aimesh_topology.html:/www/aimesh/aimesh_topology.html \
    --property=StandardOutput=append:/tmp/leon-aimesh/namespace.stdout \
    --property=StandardError=append:/tmp/leon-aimesh/namespace.stderr \
    /usr/sbin/httpds -s -p 443
