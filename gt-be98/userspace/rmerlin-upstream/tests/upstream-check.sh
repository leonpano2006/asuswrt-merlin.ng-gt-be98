#!/bin/busybox sh
set -eu
mkdir -p /run/upstream-check
cd /run/upstream-check
for app in /usr/sbin/rc /usr/sbin/httpd /usr/sbin/infosvr /usr/sbin/inadyn /usr/sbin/Tor /usr/sbin/openvpn /usr/sbin/dnsmasq /usr/sbin/miniupnpd /usr/sbin/miniupnpd-igdv2 /usr/lib/arm-linux-gnueabi/ipsec/charon; do
    LD_TRACE_LOADED_OBJECTS=1 LD_WARN=1 LD_BIND_NOW=1 "$app" > linkage 2>&1
    if grep -E 'undefined symbol|not found|cannot be preloaded' linkage; then echo "FAILED_LINKAGE $app"; exit 1; fi
done
echo LAB_UPSTREAM_EXECUTABLE_RELOCATIONS_PASS
openssl version > openssl-version
grep -q 'OpenSSL 3.5.8' openssl-version
/usr/libexec/openssl-legacy version > legacy-version
grep -q 'OpenSSL 1.1.1' legacy-version
/usr/sbin/openvpn --version > openvpn-version
grep -q 'OpenVPN 2.7.7' openvpn-version
grep -q 'OpenSSL 3.5.8' openvpn-version
/usr/sbin/Tor --version > tor-version
grep -q 'Tor version 0.4.9.11' tor-version
: > torrc
/usr/sbin/Tor --verify-config -f "$PWD/torrc" --DataDirectory /run/tor-test --DisableNetwork 1 --SocksPort 0 > tor-config-log 2>&1 || { cat tor-config-log; exit 1; }
grep -q 'Configuration was valid' tor-config-log
/usr/sbin/ipsec version > ipsec-version
grep -q '6.0.4' ipsec-version
echo LAB_UPSTREAM_VERSIONS_PASS
openssl req -new -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -x509 -days 1 -subj /CN=localhost -keyout key.pem -out cert.pem > cert-log 2>&1
openssl verify -CAfile cert.pem cert.pem
/usr/libexec/openssl-legacy x509 -in cert.pem -noout -subject | grep -q localhost
openssl s_server -accept 127.0.0.1:14443 -cert cert.pem -key key.pem -www > server-log 2>&1 &
tls_pid=$!
dns_pid=
trap 'kill "$tls_pid" ${dns_pid:-} 2>/dev/null || true' EXIT
sleep 1
printf 'GET / HTTP/1.0\r\n\r\n' | /usr/libexec/openssl-legacy s_client -connect 127.0.0.1:14443 -CAfile cert.pem -verify_return_error > client-log 2>&1
grep -q 'Verify return code: 0 (ok)' client-log
grep -q 'TLSv1.3' client-log
kill "$tls_pid"; wait "$tls_pid" || true
trap - EXIT
echo LAB_TLS35_SERVER_LEGACY11_CLIENT_PASS
openvpn --genkey secret vpn-secret
openvpn --test-crypto --secret vpn-secret --cipher AES-256-GCM --verb 3 > vpn-crypto-log 2>&1
grep -q 'OpenVPN crypto self-test mode SUCCEEDED' vpn-crypto-log
openvpn --genkey tls-crypt-v2-server v2-server
openvpn --tls-crypt-v2 v2-server --genkey tls-crypt-v2-client v2-client
test -s v2-client
echo LAB_OPENVPN_CRYPTO_AND_TLSCRYPTV2_PASS
cat > dnsmasq.conf <<'EOF'
port=1053
no-resolv
no-hosts
bind-interfaces
listen-address=127.0.0.1
user=root
group=root
pid-file=/run/upstream-check/dnsmasq.pid
address=/upstream.test/192.0.2.9
EOF
dnsmasq --test --conf-file="$PWD/dnsmasq.conf"
dnsmasq --keep-in-foreground --conf-file="$PWD/dnsmasq.conf" > dns-log 2>&1 &
dns_pid=$!
trap 'kill "$dns_pid" 2>/dev/null || true' EXIT
sleep 1
/usr/libexec/dns-probe
kill "$dns_pid"; wait "$dns_pid" || true
trap - EXIT
EASYRSA_BATCH=1 EASYRSA_PKI="$PWD/pki" /rom/easy-rsa/easyrsa init-pki > easyrsa-log 2>&1
test -d pki/private
echo LAB_EASYRSA3_LAYOUT_PASS
echo LAB_UPSTREAM_ALL_PASS
