#!/usr/bin/bash
set -euo pipefail
export PATH=/usr/bin:/usr/sbin:/bin:/sbin SYSTEMD_PAGER=cat SYSTEMD_COLORS=0
work=$(mktemp -d /run/leon7-features-XXXXXX)
unit=leon7-journal-probe.service
server=''
cleanup() {
    if [[ -n $server ]]; then kill "$server" 2>/dev/null || true; wait "$server" 2>/dev/null || true; fi
    systemctl stop "$unit" >/dev/null 2>&1 || true
    rm -f "/run/systemd/system/$unit"
    systemctl daemon-reload
    rm -r "$work"
}
trap cleanup EXIT
version=$(systemctl --version)
for feature in OPENSSL CURL ZLIB ZSTD BLKID; do grep -q "+$feature" <<<"$version"; done
echo LIVE_SYSTEMD_FEATURE_FLAGS_PASS
/usr/sbin/sysctl --version | grep -q 'procps-ng 4.0.7'
[[ $(/usr/sbin/sysctl -n kernel.osrelease) == $(uname -r) ]]
[[ $(/usr/sbin/sysctl -n net.ipv4.ip_forward) == $(cat /proc/sys/net/ipv4/ip_forward) ]]
/usr/lib/systemd/systemd-sysctl --version | head -1
echo LIVE_SYSCTL_READONLY_PASS
printf 'leon7 ephemeral credential test\n' >"$work/plain"
export SYSTEMD_CREDENTIAL_SECRET="$work/hostkey"
systemd-creds encrypt --name=probe --with-key=host "$work/plain" "$work/encrypted"
systemd-creds decrypt --name=probe "$work/encrypted" "$work/decrypted"
cmp "$work/plain" "$work/decrypted"
if systemd-creds decrypt --name=wrong "$work/encrypted" "$work/wrong" 2>"$work/rejected"; then exit 1; fi
echo LIVE_OPENSSL_CREDENTIALS_PASS
cat >"$work/message" <<'EOF'
#!/bin/busybox sh
i=0
while test "$i" -lt 300; do
    printf 'LEON7-ZSTD-%04d abcdefghijklmnopqrstuvwxyz-repeated-journal-data ' "$i"
    i=$((i+1))
done
echo
EOF
cat >"/run/systemd/system/$unit" <<EOF
[Service]
Type=oneshot
ExecStart=/bin/busybox sh $work/message
StandardOutput=journal
EOF
systemctl daemon-reload
systemctl start "$unit"
journalctl --sync
journalctl --header >"$work/header"
grep COMPRESSED-ZSTD "$work/header"
journalctl --no-pager -o cat -u "$unit" >"$work/message-read"
grep -q LEON7-ZSTD-0299 "$work/message-read"
echo LIVE_ZSTD_JOURNAL_WRITE_READ_PASS
/usr/libexec/openssl4 req -new -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -noenc -keyout "$work/tls.key" -out "$work/tls.crt" -days 1 -subj /CN=localhost -addext subjectAltName=DNS:localhost >"$work/tls-create.log" 2>&1
/usr/libexec/openssl4 s_server -accept 127.0.0.1:24443 -key "$work/tls.key" -cert "$work/tls.crt" -tls1_3 -www -naccept 1 >"$work/tls-server.log" 2>&1 &
server=$!
sleep 1
/tmp/leon7-probes/curl-native-test --noproxy '*' --fail --silent --show-error --max-time 15 --cacert "$work/tls.crt" --resolve localhost:24443:127.0.0.1 https://localhost:24443/ >"$work/tls-result"
wait "$server";server=''
grep -q s_server "$work/tls-result"
echo LIVE_NATIVE_CURL_OPENSSL4_TLS13_PASS
/usr/bin/bash /tmp/leon7-probes/shell-coreutils-check.bash
for kind in tcp udp; do
    /usr/bin/iperf3 -s -1 -B 127.0.0.1 -p 25201 >"$work/iperf-server" 2>&1 &
    server=$!;sleep 1
    args=(-P 2 -Z)
    if [[ $kind == udp ]]; then args=(-u -b 1M); fi
    /usr/bin/iperf3 -c 127.0.0.1 -4 -p 25201 -t 1 --json "${args[@]}" >"$work/iperf-$kind.json"
    wait "$server";server=''
    /usr/gnu/bin/jq -e '(has("error") | not) and ((.end.sum_received.bytes // .end.sum.bytes) > 0)' "$work/iperf-$kind.json"
done
echo LIVE_IPERF_TCP_UDP_ZERO_COPY_PASS
touch /run/leon7-live-features-passed
echo LIVE_LEON7_FEATURES_ALL_PASS
