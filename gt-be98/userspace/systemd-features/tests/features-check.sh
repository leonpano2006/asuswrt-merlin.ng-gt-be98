#!/bin/busybox sh
set -eu
version=$(systemctl --version)
for feature in OPENSSL CURL ZLIB ZSTD BLKID; do printf '%s\n' "$version" | grep -q "+$feature"; done
echo LAB_SYSTEMD_FEATURE_FLAGS_PASS
# All parameter writes happen only in the offline QEMU guest.
sysctl --version | grep -q 'procps-ng 4.0.7'
test "$(sysctl -n kernel.osrelease)" = "$(uname -r)"
oldhost=$(sysctl -n kernel.hostname)
sysctl -q -w kernel.hostname=leon-sysctl-qemu
test "$(sysctl -n kernel.hostname)" = leon-sysctl-qemu
sysctl -q -w "kernel.hostname=$oldhost"
old_domain=$(sysctl -n kernel.domainname)
printf 'kernel.domainname = leon-procps-qemu\n' > /run/sysctl-leon-test.conf
sysctl --dry-run -p /run/sysctl-leon-test.conf
test "$(sysctl -n kernel.domainname)" = "$old_domain"
sysctl -q -p /run/sysctl-leon-test.conf
test "$(sysctl -n kernel.domainname)" = leon-procps-qemu
sysctl -q -w "kernel.domainname=$old_domain"
/usr/lib/systemd/systemd-sysctl --prefix=kernel.domainname /run/sysctl-leon-test.conf
test "$(sysctl -n kernel.domainname)" = leon-procps-qemu
sysctl -q -w "kernel.domainname=$old_domain"
/usr/libexec/test-sysctl-util >/run/test-sysctl-util.log 2>&1
echo LAB_PROCPS_AND_SYSTEMD_SYSCTL_PASS
printf 'GT-BE98 systemd credential test\n' >/run/plain-credential
export SYSTEMD_CREDENTIAL_SECRET=/run/leon-credential.secret
systemd-creds encrypt --name=probe --with-key=host /run/plain-credential /run/credential.enc
systemd-creds decrypt --name=probe /run/credential.enc /run/credential.dec
cmp /run/plain-credential /run/credential.dec
if systemd-creds decrypt --name=wrong /run/credential.enc /run/wrong-credential 2>/run/wrong-credential.log; then exit 1; fi
echo LAB_SYSTEMD_OPENSSL_CREDENTIALS_PASS
cat >/run/leon-journal-message.sh <<'EOF'
#!/bin/busybox sh
i=0
while test "$i" -lt 300; do
    printf 'LEON-ZSTD-COMPRESSION-%04d repeated-data-abcdefghijklmnopqrstuvwxyz ' "$i"
    i=$((i+1))
done
echo
EOF
cat >/run/systemd/system/leon-compressed-journal.service <<'EOF'
[Service]
Type=oneshot
ExecStart=/bin/busybox sh /run/leon-journal-message.sh
StandardOutput=journal
EOF
systemctl daemon-reload
systemctl start leon-compressed-journal.service
journalctl --sync
journalctl --header >/run/journal-header
cat /run/journal-header
grep -q COMPRESSED-ZSTD /run/journal-header
journalctl --no-pager -o cat -u leon-compressed-journal >/run/zstd-message
grep -q LEON-ZSTD-COMPRESSION-0299 /run/zstd-message
echo LAB_JOURNAL_ZSTD_WRITE_AND_READ_PASS
# curl helper is test-only; libcurl and its TLS/compression dependencies are production files.
ip link set lo up
/usr/libexec/openssl4 req -new -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -noenc -keyout /run/tls.key -out /run/tls.crt -days 1 -subj /CN=localhost -addext subjectAltName=DNS:localhost >/run/tls-cert.log 2>&1
/usr/libexec/openssl4 s_server -accept 127.0.0.1:24443 -key /run/tls.key -cert /run/tls.crt -tls1_3 -www -naccept 1 >/run/tls-server.log 2>&1 &
server=$!
sleep 1
/usr/libexec/curl-native-test --noproxy '*' --fail --silent --show-error --max-time 15 --cacert /run/tls.crt --resolve localhost:24443:127.0.0.1 https://localhost:24443/ >/run/tls-result
wait "$server"
grep -q 's_server' /run/tls-result
echo LAB_NATIVE_CURL_OPENSSL4_TLS13_PASS
/usr/libexec/shell-coreutils-check.bash
iperf_case() {
    label=$1;addr=$2;shift 2
    /usr/bin/iperf3 -s -1 -B "$addr" -p 25201 >/run/iperf-server.log 2>&1 &
    server=$!
    sleep 1
    /usr/bin/iperf3 -c "$addr" -p 25201 -t 1 --json "$@" >/run/iperf-$label.json
    wait "$server"
    /usr/gnu/bin/jq -e '(has("error") | not) and ((.end.sum_received.bytes // .end.sum.bytes) > 0)' /run/iperf-$label.json
}
iperf_case tcp4 127.0.0.1 -4 -P 2 -Z
iperf_case tcp6 ::1 -6 -R
iperf_case udp4 127.0.0.1 -4 -u -b 1M
echo LAB_DYNAMIC_IPERF_TCP4_TCP6_UDP_ZERO_COPY_PASS
echo LAB_FEATURES_ALL_PASS
