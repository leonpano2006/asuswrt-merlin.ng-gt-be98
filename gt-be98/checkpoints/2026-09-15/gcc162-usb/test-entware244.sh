#!/bin/sh
set -eu
LIB=/opt/lib.leon244-20260914
LOADER=/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1
run() { "$LOADER" --inhibit-rpath '' --library-path "$LIB:$LIB/perl5/5.40/CORE:/lib/aarch64-linux-gnu" "$@"; }
run /opt/bin/bash -c 'printf "Entware bash runs\n"'
run /opt/bin/make --version | head -n 1
run /opt/bin/as --version | head -n 1
run /opt/bin/ld --version | head -n 1
run /opt/bin/gcc --version | head -n 1
if [ -x /opt/bin/perl ]; then
    run /opt/bin/perl -MSocket -e 'my ($e,@r)=Socket::getaddrinfo("example.com",80); die $e if $e; die "DNS empty" unless @r; die "crypt failed" unless length crypt("test","ab"); print "Perl DNS + crypt PASS\n";'
fi
if [ -x /opt/bin/git ]; then run /opt/bin/git --version; fi
if [ -x /opt/bin/curl ]; then run /opt/bin/curl --version | head -n 1; fi
printf 'ENTWARE244_PRECHECK_PASSED\n'
