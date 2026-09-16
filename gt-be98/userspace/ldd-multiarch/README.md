# Restore multiarch ldd through the writable tool prefixes

The firmware's `/usr/bin/ldd` already supports aarch64, armel and armhf. The
separate `/opt/bin/ldd` listed only `/opt/lib/ld-linux-aarch64.so.1`, so it
incorrectly reported 32-bit executables as not dynamically linked. Entware's
profile can put `/opt/bin` ahead of the firmware tools in PATH.

The live fix preserves one canonical implementation:

```
/usr/local/bin/ldd -> /usr/bin/ldd
/opt/bin/ldd       -> /usr/bin/ldd
```

`scripts/install-live.bash` pins the previous and canonical script hashes,
checks the writable `/usr/local` mount, saves the old script, installs the two
links and validates three ABIs. It restores the prior entries if installation
or its checks fail. The saved old file is
`/usr/local/share/leon-backups/ldd-20260916/opt-bin-ldd`.
`scripts/restore-live.bash` is an explicit undo, not an automatic boot hook.
The old script remains available for recovery and must not shadow the fixed
tool in PATH. No firmware file, startup profile, library, network setting or
boot metadata is changed. The links persist on the existing USB filesystem.

The installer is a historical, exact-state procedure: run it only against the
pinned old state and do not rerun after installation. A future package upgrade
could replace `/opt/bin/ldd`; `/usr/local/bin/ldd` remains the preferred local
entry and continues to use the firmware implementation. This checkpoint is an
external runtime dependency, not a newly flashed firmware image.

## Validation

All 15 cases pass: each of `/usr/bin/ldd`, `/usr/local/bin/ldd` and `/opt/bin/ldd`
against aarch64 bash, armel BusyBox, vendor rc, a real armhf ABI probe, and
Entware's aarch64 bash. Every case resolves libc from its expected directory.
Verbose/multiple-file handling, a missing-file nonzero exit, both PATH priority
orders and a fresh login shell also pass. The armhf probe comes from the pinned
preceding multiarch-loader checkpoint; its SHA-256 is
`2c85ee23010aaa0d180c17d2fb38a0f8316045c39c5c8bac431e0ca030d1b1eb`.
The temporary test directory was removed after verification.

Canonical ldd SHA-256:
`251bf4507a2b1e6a5ad062bc88493d52f688dea5c4fcac2a199e5fc04247d732`.
Old `/opt/bin/ldd` SHA-256:
`af1ef718ebc9d104434124eca35a08f391af73899685dc4ca308f43685d6f5c7`.
Both historical signed firmware images and the unflashed libgcc candidate
remain unchanged. No reboot or firmware commit was performed.

## libgcc ISA investigation

The exact GCC 15.2 Ubuntu candidates have these ELF attributes:

| Runtime | ISA baseline |
| --- | --- |
| Candidate armel GCC 15.2 | ARMv5T, soft-float ABI |
| Candidate armhf GCC 15.2 | ARMv7-A, Thumb-2, VFPv3-D16, hard-float ABI |
| Currently installed armel GCC 10.3 | ARMv7-A, Thumb-2, VFPv3 |

These are modern GCC runtime versions with generic ISA targets; the armel
candidate's ISA baseline is indeed lower than the current file. It remains
compatible with the router, as shown by the preceding QEMU and real-device
unwind/arithmetic/C++ tests. A library's baseline does not change instructions
already compiled into the program or its other libraries.

Libgcc supplies arithmetic helpers and exception unwinding, rather than being
the primary AES/SHA/CRC implementation; see the
[GCC internals documentation](https://gcc.gnu.org/onlinedocs/gccint/Libgcc.html).
ISA tuning can still matter to arithmetic helpers. Disassembly of the exact
candidate armel and armhf `__divsi3`/`__udivsi3` routines shows software division,
with no SDIV/UDIV. The current armel GCC 10 runtime also uses software division
in these routines, so this particular replacement is not switching existing
hardware division to software. The implementations and instruction counts
differ, and instruction count alone does not predict execution time.

66 deployed ELF consumers have versioned imports of division/modulus helpers.
Their call frequency is unknown. No live performance benchmark was run, and
equal speed or negligible impact is not established. A custom A53-targeted
runtime could improve relevant helper paths; it would need to preserve softfp
versus hard-float ABI, exported symbol versions, and unwinding behavior. CRC and
crypto flags alone do not automatically accelerate ordinary arithmetic.
This task does not change the already prepared runtime libraries or flash the
candidate. Detailed ELF attributes, disassembly and consumers are in evidence/.
