#!/bin/sh
set -eu
test "$(sha256sum /usr/bin/bash | cut -d " " -f1)" = cfff7a1c689ffeb26bfe883a16c0999bf7ba2e3f2a58b3e4aafc456cadb971f7
test "$(sha256sum /usr/bin/iperf3 | cut -d " " -f1)" = f7de0985bd14c8be6a4bbef74575cd75a57eeede9e995e28f2852779c7b71713
test "$(sha256sum /usr/bin/journalctl | cut -d " " -f1)" = d5d641e740dae180300a53322b12a027c0a77c89a23ed403372277b5e297bd80
test "$(sha256sum /usr/bin/systemctl | cut -d " " -f1)" = 3b421bc115048d452699f5a66c3dabb99e9c9a1093b9d1680939abc4800f4c66
test "$(sha256sum /usr/bin/systemd-notify | cut -d " " -f1)" = f854b2142f4b494182906ee2efdc8468c0d4a587a5d8fcbe5954daf6c517ba17
test "$(sha256sum /usr/bin/systemd-run | cut -d " " -f1)" = 79d1926e1db42e7febfa921ac4df384b85759c487b0a960201ede8faa07e5e44
test "$(sha256sum /usr/gnu/bin/coreutils | cut -d " " -f1)" = 4deb5f83dd330dd186be6ee68f683bad29d4634b9c057f704a0b6b4e310b1dab
test "$(sha256sum /usr/lib/aarch64-linux-gnu/systemd/libsystemd-core-257.so | cut -d " " -f1)" = 5ee9bdd76271b36977f28c176cbaee0a01a0c01fac520aef8d0a76df5affa5ec
test "$(sha256sum /usr/lib/aarch64-linux-gnu/systemd/libsystemd-shared-257.so | cut -d " " -f1)" = fd2b51b8fcd66437ef6a1d5cdf729c60afce2aee1bab93acf354061e5275474c
test "$(sha256sum /usr/lib/systemd/systemd | cut -d " " -f1)" = 34eae69481b8ec1d756ad995e67be0a800b50220f94adcb226ad9d9c01a875a3
test "$(sha256sum /usr/lib/systemd/systemd-executor | cut -d " " -f1)" = 5c051c4d6a653556bc0f53025d77200d8a67416b4a57a425bb6dac01b5f8cf25
test "$(sha256sum /usr/lib/systemd/systemd-journald | cut -d " " -f1)" = 2cf90af51d1176f60d3d2e44e3fffa9c26e427c5d0468fa4d4b80c0eb0e8aa26
test "$(sha256sum /usr/lib/systemd/systemd-shutdown | cut -d " " -f1)" = a01bb5814d81d9cacc32ed338683b8e34b0f6df1c0a710c8b223f2500d362d37
test "$(sha256sum /usr/share/leon-upstream.json | cut -d " " -f1)" = acf2b0a37c6c80bcc49ed17b2c7624a57a9528ca7b13ee4e21aeb05e04171e9c
test "$(sha256sum /usr/bin/systemd-creds | cut -d " " -f1)" = 317a1749010bc5b09189fbd43fb7e1f4438acf1ae65095894134c54ba0fda072
test "$(readlink /usr/lib/aarch64-linux-gnu/libcurl.so.4)" = libcurl.so.4.8.0
test "$(sha256sum /usr/lib/aarch64-linux-gnu/libcurl.so.4.8.0 | cut -d " " -f1)" = 6966be1509f098ec2525bc37f8cc63e9cd42b969ab53451c03ff2814bb7fdf40
test "$(sha256sum /usr/lib/systemd/systemd-sysctl | cut -d " " -f1)" = 217f3b18aad2b472481f51fe28813de4b832113438ed31b84b7e7d131ac18905
test "$(sha256sum /usr/sbin/sysctl | cut -d " " -f1)" = 3127dca99e1134d096d1f67a8086b54267d6c252270a55f583007f46b74d711f
test "$(sha256sum /usr/sbin/rc | cut -d " " -f1)" = ca786145c19101bbfd4bb540aff3fbd3895d7dc47a2a7d476319d0a4009226a8
test "$(sha256sum /usr/sbin/httpd | cut -d " " -f1)" = e1c6013f9e535cd76294a4acc814b5b985fb487e79dff60066b18d52cd8bf450
test "$(sha256sum /usr/sbin/init | cut -d " " -f1)" = d28e8bfa21f9c95ac8c9672e3d12686147759c2ea88ef65a1f81c75cb00c0c2f
awk '$2=="/tmp/mnt/JFFS" && $3=="btrfs"{ok=1}END{exit !ok}' /proc/mounts
echo LIVE_FILES_SHA256_AND_USB_MOUNT_PASS
