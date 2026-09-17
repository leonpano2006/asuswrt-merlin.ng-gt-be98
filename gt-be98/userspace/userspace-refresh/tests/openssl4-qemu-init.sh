#!/bin/sh
export PATH=/bin:/usr/bin:/usr/sbin
echo QEMU_LAB_INIT_REACHED
set -eu
trap 'echo LAB_OPENSSL4_CHECK_FAILURE; poweroff -f' EXIT
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mkdir -p /tmp /run /var/lib/systemd
umask 077
export OPENSSL_CONF=/usr/lib/ssl/openssl4/openssl.cnf
o4() { /usr/libexec/openssl4 "$@"; }
o3() { OPENSSL_CONF=/dev/null /usr/sbin/openssl "$@"; }
creds() {
    /lib/ld-linux-aarch64.so.1 --library-path /probe:/usr/lib/aarch64-linux-gnu \
        /probe/systemd-creds "$@"
}
test "$(uname -r)" = 4.19.294
o4 version | grep -q '^OpenSSL 4.0.2 '
o3 version | grep -q '^OpenSSL 3.5.8 '
echo LAB_OPENSSL4_AND_ARM32_358_LOAD_PASS
printf 'GT-BE98 OpenSSL 4 A53 compatibility\n' > /tmp/plain
o4 dgst -sha256 /tmp/plain > /tmp/digest4
o3 dgst -sha256 /tmp/plain > /tmp/digest3
cmp /tmp/digest3 /tmp/digest4
o4 rand -hex 32 > /tmp/random
test "$(wc -c < /tmp/random)" -eq 65
o4 req -new -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 \
    -noenc -keyout /tmp/key.pem -out /tmp/cert.pem -days 1 \
    -subj /CN=localhost -addext subjectAltName=DNS:localhost
o4 x509 -in /tmp/cert.pem -pubkey -noout > /tmp/pub.pem
o4 dgst -sha256 -sign /tmp/key.pem -out /tmp/signature /tmp/plain
o3 dgst -sha256 -verify /tmp/pub.pem -signature /tmp/signature /tmp/plain | grep -q 'Verified OK'
echo LAB_OPENSSL4_ARM32_SIGNATURE_INTEROP_PASS
ip link set lo up
o4 s_server -accept 127.0.0.1:24443 -key /tmp/key.pem -cert /tmp/cert.pem \
    -tls1_3 -www -naccept 1 > /tmp/server4.log 2>&1 &
server=$!
sleep 1
printf 'GET / HTTP/1.0\r\n\r\n' | o3 s_client -connect 127.0.0.1:24443 \
    -tls1_3 -quiet -verify_return_error -verify_hostname localhost -CAfile /tmp/cert.pem \
    > /tmp/client3.log 2>&1
wait "$server"
grep -q 'HTTP/1.0 200' /tmp/client3.log
o3 s_server -accept 127.0.0.1:24444 -key /tmp/key.pem -cert /tmp/cert.pem \
    -tls1_3 -www -naccept 1 > /tmp/server3.log 2>&1 &
server=$!
sleep 1
printf 'GET / HTTP/1.0\r\n\r\n' | o4 s_client -connect 127.0.0.1:24444 \
    -tls1_3 -quiet -verify_return_error -verify_hostname localhost -CAfile /tmp/cert.pem \
    > /tmp/client4.log 2>&1
wait "$server"
grep -q 'HTTP/1.0 200' /tmp/client4.log
echo LAB_OPENSSL4_ARM32_TLS13_BOTH_DIRECTIONS_PASS
export SYSTEMD_CREDENTIAL_SECRET=/tmp/credential.secret
creds encrypt --name=probe --with-key=host /tmp/plain /tmp/encrypted
creds decrypt --name=probe /tmp/encrypted /tmp/decrypted
cmp /tmp/plain /tmp/decrypted
if creds decrypt --name=wrong /tmp/encrypted /tmp/wrong 2>/tmp/wrong.log; then exit 1; fi
echo LAB_SYSTEMD257_OPENSSL4_HOST_CREDENTIAL_ROUNDTRIP_PASS
o4 list -providers -provider default -provider legacy | grep -q legacy
echo LAB_OPENSSL4_LEGACY_PROVIDER_LOAD_PASS
echo LAB_OPENSSL4_ALL_PASS
trap - EXIT
poweroff -f
