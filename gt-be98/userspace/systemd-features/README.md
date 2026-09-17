# GT-BE98 leon7: systemd features and full sysctl

Candidate based on the successfully tested leon6 checkpoint (Git parent
`ea206ced7a48e30c8be38a49217ef7e36b177aeb`). It is not flashed. Production
continues to run leon6. The only live change in this checkpoint is the full
procps-ng 4.0.7 sysctl at `/usr/local/sbin/sysctl`; its live tests were read-only.
The candidate includes the same executable internally at `/usr/sbin/sysctl`.
No kernel parameters, firmware commit flags or rollback targets were changed.

Systemd remains 257.13 with the existing service profile and now reports
`+OPENSSL +BLKID +CURL +ZLIB +ZSTD`. Default journal compression is zstd.
The native dependencies are OpenSSL 4.0.2, curl 8.22.0, zlib 1.3.2,
zstd 1.5.7 and blkid 2.42.2. The new systemd-creds and systemd-sysctl tools
are included. Enabling these libraries does not install additional systemd
daemons or automatically apply sysctl settings at boot. ASUS ARMEL TLS
libraries, kernel #36, all 182 modules, rc, init and existing units are unchanged.
Only optional ARMHF libraries remain on USB, at their existing system-libs path.

All new target builds run on DGX with GCC 16.2.0, glibc 2.44 and
`-mcpu=cortex-a53+crc+crypto`, using size optimization and LTO. ELF files
retain SHA1 GNU build IDs, which are identifiers rather than digital signatures.
The original RSA-PSS signed bootfs is verified and preserved byte-for-byte.

To fit the additional libraries without removing features, Bash 5.3.15 and
coreutils 9.11 were rebuilt with -Oz/LTO. Builtins, shell options and coreutils
applets match the originals. iperf3 3.21 retains its optional feature list and
now uses the already included internal glibc instead of embedding another copy.
libcurl preserves all configured protocols and its 100 public exports; upstream
symbol hiding and effective -Oz remove unnecessary internal exports/code.

Final rootfs: 78,282,752 bytes; limit: 78,565,376; headroom: 282,624 (276 KiB).
It is 176,128 bytes smaller than leon6 despite the added features. The flasher's
1 MiB allowance for EACH bootfs/rootfs is retained: 107+625=732 of 734 available
LEBs. No rollback volume is reduced. SquashFS uses zstd 1.5.7 level 22,
1 MiB blocks, tail-end packing and family-name sorting. The full FIT image is
90,700,876 bytes. See the candidate manifest for exact payload and image hashes.

Validation includes native OpenSSL/compression/cryptolib tests; local HTTP/HTTPS
plain, gzip and zstd responses; and rejection of untrusted TLS certificates.
The exact final SquashFS unpacks to identical bytes, modes and symlinks.
All 334 native/ARMEL executable loader closures pass without USB on kernel #36.
All five modern/legacy runtime and C++ probe sets pass before and after ldconfig,
including ARMHF with simulated USB and native operation after USB removal.

The full PID1 and service rehearsals use the real kernel #36 under offline
Cortex-A53 QEMU. No host NIC, disk or router hardware is exposed. Production
paths are byte/mode/link-identical; added probes simulate ASUS hardware-facing
backends and the USB payload. Tests exercise sysctl writes/restoration only
inside the VM, systemd credential encryption and wrong-name rejection, actual
zstd journal writes and reads, TLS 1.3, Bash features, coreutils file operations,
and iperf3 IPv4/IPv6/UDP/multiple streams/zero-copy. Existing cgroup v1/hybrid,
rc ownership, OpenVPN caller roles, service recovery, shutdown drainage,
cron, haveged, infosvr, mDNS and NTP checks are retained.

This is bounded compatibility testing. Kernel 4.19 remains below systemd 257's
upstream 5.4 baseline; QEMU does not validate the physical Broadcom datapath.
The candidate needs a separate hardware trial before acceptance. Hardware
acceleration checks from leon6 are not claimed as leon7 physical evidence.

## Rebuild and recovery inputs

This is an out-of-tree checkpoint, not a standalone replacement ASUS SDK.
Restore the recorded parent checkpoints and compiler repository first.
`configs/dependencies.json` identifies the parent rootfs, compiler, source and
rehearsal inputs. `configs/sources.json` pins newly downloaded upstream archives;
`configs/source-snapshots.json` pins the clean existing Bash, coreutils and iperf
sources saved on DGX and ML350. The backup also contains the sysroot, staged
binaries, candidate, source archives, build commands and original test output.
The source code of upstream packages is unchanged; the integration/build/test
code is under scripts, tests and live and is published to our Git branch.

Fresh build order within restored sibling checkpoints:

1. Restore clean source snapshots; fetch the pinned curl/procps archives.
2. `prepare-sdk.py`, `build-procps.py`, `build-curl.py`, `build-systemd.py`,
   `stage-systemd.py`; then `build-small-tools.py bash`,
   `build-small-tools.py coreutils`, `build-iperf.py`.
3. Run `test-native.py` and `test-curl.py`; `finalize-root.py`, `test-parity.py`.
4. Run `measure.py build/production-rootfs features-final-v2 --zstd157`,
   `test-closure.py`, `pack-rehearsal.py --revision features-v3`, then the
   default/services/network_services QEMU suites (180-second bound).
5. `pack-rootfs.py` requires the exact hashes in packaging-policy.json and
   verifies the signed bootfs and preserved kernel. Revalidate policy hashes
   after any rebuild rather than reusing an old policy with different output.

Scripts derive checkpoint paths from their locations; recorded commands retain
the actual build paths for audit. The replay uses the existing GCC toolchain
checkpoint, which has its own repository. Run from a fresh build directory;
most scripts deliberately refuse to overwrite completed builds.

Two failed rehearsal iterations were test-harness issues: the first used
systemd-run's unavailable system bus, replaced by a normal unit; the second
ran an ARMHF ABI probe before installing the simulated USB. Their original
logs are retained. Final acceptance requires the complete v3 suites. The
initial curl probe was overridden to -O2 and lacked symbol hiding; only the
corrected curl-hidden build is selected. iperf's upstream configure macro
treats even `--disable-static-bin` as enabling static linking; the final recipe
omits that option and asserts the AArch64 dynamic interpreter explicitly.

The current router's `/usr/local/sbin` precedes `/usr/sbin` in its interactive
PATH, so the already installed sysctl will still be selected after a future
flash; both copies have the same hash. A future flash must first return to
committed slot2, recheck the current slot1/rollback hashes and capacity, write
only inactive slot1 and request a once-only boot. Nothing in this checkpoint
commits firmware or changes rollback automatically.
