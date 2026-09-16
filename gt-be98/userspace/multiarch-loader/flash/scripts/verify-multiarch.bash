#!/usr/bin/bash
set -eu
work=/tmp/leon-ubuntu-verify
test -d "$work"
unset LD_LIBRARY_PATH LD_PRELOAD
test "$(readlink /lib)" = usr/lib
sha256sum -c "$work/runtime.sha256"
sha256sum -c "$work/libraries.sha256"
sha256sum -c "$work/hooks-config.sha256"
removed=0
while read -r path; do
  test ! -e "$path" && test ! -L "$path"
  removed=$((removed+1))
done < "$work/aliases-remove.txt"
kept=0
while read -r path target; do
  test "$(readlink "$path")" = "$target"
  test -e "$path"
  kept=$((kept+1))
done < "$work/aliases-keep.txt"
test "$removed" = 257 && test "$kept" = 32
printf 'LIVE_ALIAS_SUMMARY removed=%s retained=%s\n' "$removed" "$kept"
for abi in aarch64 armel armhf; do
  case "$abi" in
    aarch64) loader=/lib/ld-linux-aarch64.so.1; triplet=aarch64-linux-gnu;;
    armel) loader=/lib/ld-linux.so.3; triplet=arm-linux-gnueabi;;
    armhf) loader=/lib/ld-linux-armhf.so.3; triplet=arm-linux-gnueabihf;;
  esac
  grep -Fxq "/usr/local/lib/$triplet" "/etc/ld.so.conf.d/$triplet.conf"
  grep -Fxq "/usr/lib/$triplet" "/etc/ld.so.conf.d/$triplet.conf"
  "$loader" --list-diagnostics | grep -E '^dl_dst_lib=|^path\.' > "$work/loader-$abi.actual"
  cmp "$work/loader-$abi.actual" "$work/loader-$abi.expected"
  cat "$work/loader-$abi.actual"
  "$work/abi-probe-$abi"
  GCONV_PATH="$work/gconv-$abi" "$work/libc-smoke-$abi"
  echo "LIVE_ABI_GLIBC_UBUNTU_PATHS_PASS $abi"
done
"$work/library-probe"
for mode in no-cache cached; do
  count=0
  failed=0
  while read -r loader program; do
    count=$((count+1))
    args=()
    if [ "$mode" = no-cache ]; then args+=(--inhibit-cache); fi
    if ! "$loader" "${args[@]}" --list "$program" > "$work/linker.out" 2>&1; then
      printf 'LINKER_FAILURE %s %s\n' "$mode" "$program"
      cat "$work/linker.out"
      failed=$((failed+1))
    fi
  done < "$work/dynamic-executables.txt"
  printf 'LIVE_LINKER_SUMMARY mode=%s count=%s failed=%s\n' "$mode" "$count" "$failed"
  test "$count" = 312 && test "$failed" = 0
done
cat > "$work/lighttpd-test.conf" <<'CONF'
server.document-root = "/www"
server.errorlog = "/tmp/leon-ubuntu-verify/lighttpd-test.log"
server.pid-file = "/tmp/leon-ubuntu-verify/lighttpd-test.pid"
server.modules = ("mod_access", "mod_alias", "mod_auth", "mod_redirect", "mod_rewrite", "mod_dirlisting", "mod_staticfile")
CONF
/usr/sbin/lighttpd -tt -f "$work/lighttpd-test.conf"
/usr/sbin/iptables -m tcp -h > "$work/iptables-help"
/usr/sbin/ipsec --version
/usr/sbin/ldconfig -p | grep -E 'libz\.so\.1|libexpat\.so\.1|libjson-c\.so\.2|libcap-ng\.so\.0'
echo UBUNTU_MULTIARCH_LIVE_LIBRARIES_PASS
