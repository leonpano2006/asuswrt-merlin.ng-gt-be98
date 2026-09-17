# GT-BE98 AiMesh and client-list compatibility fix

The running leon8 management service now reads its existing AiMesh node and
client tables, renders topology and client details, and survives repeated
traffic updates. The fix is applied in RAM. No firmware was flashed or committed.

## Root causes and changes

1. `CM_CLIENT_TABLE` used host-toolchain `time_t` in shared memory. Ubuntu ARMEL
   GCC 15 defaults to time64, while the unchanged vendor `cfg_server` publishes
   the time32 structure. The HTTPD request was 20,424 bytes for a 20,348-byte
   segment. Keep this ARM32 wire field explicitly `int32_t`; application time64
   remains enabled. Return an empty JSON array on shared-memory access errors.
2. The newer upstream networkmap header added `mlo_links` and `is_re` fields,
   making the client table 384,072 bytes. The retained GT-BE98 producer publishes
   322,356 bytes. `NMP_LEGACY_CLIENT_TABLE`, selected for the current GT-BE98 BSP,
   preserves that producer layout and skips only the new fields it cannot supply.
   Existing MLO fields and radio operation remain unchanged. Revisit this switch
   when upgrading the actual networkmap producer/SDK; do not change only one side.
3. Both wired-MAC JSON formatters advanced a buffer pointer but still passed
   the entire array size to `snprintf`. Once the node table became readable,
   FORTIFY correctly rejected a 1,024-byte bound with only 1,023 bytes remaining.
   Use the remaining capacity and stop adding entries before exceeding the array.
4. Initialize the topology list as `[]`, preventing an early asynchronous `.filter`
   call on a string. The deployed HTML is patched from the existing processed
   template so numeric translation tags and Traditional Chinese remain intact.
   The canonical source template is updated separately for normal firmware builds.

## Build and dependencies

Builds run on the DGX, not on the router: ARMEL GCC 15.2, glibc 2.44, Cortex-A53
with CRC/crypto and softfp, FORTIFY enabled, GNU SHA-1 build IDs retained.
`scripts/build.py` rebuilds HTTPD `web.o`, retaining the earlier `ej.o` translation
fix, plus latest leon9 RC consumers `init.o`, `wan.o` and `services.o` of the cfg
header. Platform service splitting, SSH and IPsec corrections are retained.
No proprietary binary is modified. Required shared libraries are unchanged and
no new undefined dynamic symbols are introduced; see `evidence/link-abi.json`.
Exact retained objects and their hashes are included in the DGX/ML350 backup.
Toolchains stay in their separate repository and are not vendored here.

Final stripped HTTPD SHA-256:
`2035aca8e26a14b0823e340ac08e2eddeb13d494d2595bc54e0014d4ba73cd0b`

Next-candidate RC SHA-256:
`cf121058ede3661d8b5a9f3bc3e8aed2850d533205b71ccf20bcf3a46c221981`

Processed HTML SHA-256:
`3cef091a58002ec0b1928473531d8c41355219cc5c1d20f6dc8bc4152f8e7e4c`

The separate Game Dashboard correction remains required:
`httpd-dashboard-fix-20260917`, libshared SHA-256
`06eb9ca13f4de144c65aad7b5e013b38b5bfa128bc4b8688e474d2c6f3e7a779`.

## Validation

- ARM QEMU byte comparisons cover all 65 cfg-table members and all 55 legacy
  networkmap-table members, including padding, against vendor-header fixtures.
  The fixed application still has eight-byte `time_t`.
- The two old MAC formatters both reproduce SIGABRT under ARM FORTIFY. Eighteen
  fixed tests cover empty, ordinary, near-capacity, oversized and long-entry
  lists, valid JSON, and unchanged surrounding canaries.
- The final root overlay is booted with the saved #36 kernel in offline QEMU;
  results and serial logs are under `builds/qemu/rc-fixed-final`. The lab has no
  physical device or network passthrough and does not emulate Broadcom radios.
- Isolated HTTPS tests pass ten API rounds, followed by a final check using the
  processed template. Normal browser login and the real topology show GT-BE98
  and an online GT-AXE16000 node, node details, and Traditional Chinese controls.
- The regular 8443 service passes twenty API rounds. The client API reports 43
  entries at verification time. RC broker PID 258 and cfg_server PID 4903 remain
  unchanged; all four radios are up and hardware L2/L3 acceleration is enabled.
- This is functional validation, not a WAN throughput benchmark or a test of
  removing/re-pairing nodes. No onboarding, mesh reset or radio restart was done.

The initial 443 diagnostic used an unstable executable bind mount. Detaching it
left the process with an invalid executable path and interfered with vendor
settings access. A private mount namespace retaining `/usr/sbin/httpd` resolves
this: the same supplied credentials successfully authenticate. The user approved
one CAPTCHA completion; normal login then cleared the failed-attempt counter.
No account credentials, CAPTCHA enforcement or authentication code were changed.
The 443 diagnostic is stopped after deploying to the regular management service.

## Reproduce and prepare the next image

Restore the recorded parent workspace checkpoints and separate toolchain first.
Original input headers, source and retained objects are in the verified backup;
canonical pre-change files can also be recovered from parent commit
`24de71557a7f6ff4e97d77ceddc96bf4b2dbf17a` and the retained vendor source tree.

Run the layout tests and `test-maclist.py`, then `build.py` and `prepare-html.py`.
For RAM verification use `start-isolated.bash`, then normal authenticated checks
with `check-api.py` (password is prompted, never saved). `apply-ram-fix.bash`
checks hashes, stops the isolated listener and restarts only management after
mounting the new binary and processed HTML. Browser and CLI logins should be
sequential because a new login may replace the previous client session.

For firmware, use a copied leon9 production root. Stage the dashboard library
with that checkpoint's `stage-next-root.py`, then this checkpoint's staging
script. Repack through the existing zstd-22 pipeline and recheck capacity,
loader closure and protected kernel/module hashes. The already packaged leon9
image is superseded and must not be flashed unchanged. The rebuilt RC belongs
in the next candidate; the running leon8 RC was not hot-swapped.

The current RAM mounts disappear on reboot. Slot 1 remains uncommitted; slot 2
remains the committed fallback. No reboot or flash was performed for this fix.
Raw private API responses and diagnostic memory are excluded from Git and the
published backup contents. Credentials, tokens and private keys are not saved.
