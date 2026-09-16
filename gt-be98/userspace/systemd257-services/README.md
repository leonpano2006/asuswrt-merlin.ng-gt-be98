# GT-BE98 systemd 257.13 與 cron／infosvr 候選

此候選以已通過實機測試的 RMerlin 102.9 a3 為基底，將 systemd 255.22 更新至
257.13，並把 BusyBox cron 與 ASUS infosvr 的程序生命週期交給 systemd。
截至此記錄，候選已通過 QEMU、尚未刷入，不能視為已通過實機。

systemd 257.13 的最低核心是 3.15、建議基線為 5.4；此處仍用原本 4.19.294 #36，
保留上游的 old-kernel 提示。258 起最低 5.4，261 起最低 5.10，因此此次沒有直接
改用最新 261 系列。採用未修改的上游 257.13 原碼，來源 commit 與 SHA-256
固定在 `configs/sources.json`。官方版本條件見該 tag 的 README。

## 實作

- systemd、executor、shutdown、journald、systemctl、journalctl、notify/run 與
  兩個 private libraries 一起更新，舊 255 private libraries 移除。
- 在 DGX 用 GCC 16.2.0、glibc 2.44 sysroot、`-mcpu=cortex-a53+crc+crypto`、
  `-Oz`、LTO、GNU SHA-1 build ID 建置。LTO 物件的 GCC 旗標與雜湊均保存，
  不從最終 ELF 的指令外觀猜測原始編譯參數。
- rc 的三個實際來源檔、patch、GCC 15.2 編譯與連結指令一併保存。沿用 a3
  的 IPsec IFNAMSIZ 修正物件，HTTPD 邊界修正也保留。
- `asus-crond.service`：真正的 BusyBox foreground daemon；rc 的原有啟停介面
  與 cron 檔案格式不變。普通重啟保留正在跑的 cron 工作，關機則由獨立 cleanup
  單元在 storage 卸載前收尾。rc 不再重複監看 managed crond。
- `asus-infosvr.service`：沿用原二進位與 `br0` 參數，保留 modem-bridge guard。
  Type=exec 不表示 UDP 應用層已就緒；真實裝置探索待實機驗證。
- early-prepare 先掛載原有五個 v1 控制器；257.13 使用其上游支援的既有掛載
  相容路徑，加上 hybrid manager hierarchy。Docker 的 v1 memory/pids/devices
  等資源控制仍保留。本次沒有改成 unified v2。
- 核心、182 個 `.ko`、signed bootfs、靜態 early-init 和 bootloader 均不修改。
  完整責任邊界見 `OWNERSHIP.md`，Podman 路線與限制見 `PODMAN.md`。

## 驗證與大小

- #36 核心、Cortex-A53 QEMU：完整回歸 109.99 秒通過；新增服務套件 36.05 秒通過。
- 覆蓋 PID 1、daemon reexec、memory/pids、三種 userspace ABI、rc 身份與通知路由、
  haveged、TLS、DNS、OpenVPN、IPsec/HTTPD 修正、關機 drain 與卸載順序。
- 新服務測試用真實 `services.c`、dispatcher、BusyBox crond、正式 units；驗證
  READY 前啟動、單一 owner、crash restart、masked failure 不退回舊 launcher、
  正在跑的 cron 工作跨 restart 保留及管理器停止時清理。
- QEMU 中 ASUS 硬體 backend 與 infosvr discovery 是明確的測試替身，沒有測到
  Wi-Fi、Runner 吞吐量或真實 UDP 裝置探索，仍須實機測試。
- 解包後逐檔比較內容、mode、symlink；正式 rootfs 與測試中的 production 路徑一致。
- 壓縮保持 zstd 22、1 MiB blocks、tailends。把 systemd 家族 ELF 排在相鄰區塊，
  不移除其他功能。`-Oz` 本身未帶來足夠映像縮減，最終容量改善來自檔案排列。

候選：`candidate/GT-BE98_leon36-systemd257-services_zstd22.pkgtb`

- 映像：90,950,732 bytes；SHA-256 `c9a12f9dbf111fe900451b2756168f1f3506ce59235e1424b6963610cbfffba6`
- rootfs：78,532,608 bytes；SHA-256 `c747a67c8db642e35ff8f2be4c89c11d86b1e6637538dfbecb428bc2fd1b5951`
- bootfs 簽章驗證成功、內容未變；kernel SHA-256
  `f6b32cfe97b9e7e2b818fd5aaf5b0a029f52d62dcf086546fd65ebf60c6da3d4`。
- 依原 flasher 每個 volume 加 1 MiB 的保留算法，需要 107+627=734 LEB。
  目前可回收 slot1 加可用空間為 734 LEB，沒有額外未分配 LEB；每 volume 的
  1 MiB 保留未縮減，UBI 壞塊保留也沒有更動。刷入前必須重新读取容量。
- 保留已 commit 的 slot2/#35。不得對未驗證候選做 firmware commit。

## 重現與依賴

Git parent 是 `0f9e311424bcaacc118f581d3602ba15ec2675dc`。此專案是既有建置鏈的
out-of-tree checkpoint，並非單獨 clone 一個目錄就可重建的獨立 SDK。
`evidence/external-inputs.json` 記錄 238 個 rc 實際來源/header/object/library 依賴
與雜湊；私有備份附帶這些檔案、完整 sysroot、上游 systemd tarball、建置物件、
候選與 QEMU 輸入。GCC 工具鏈仍由既有獨立工具鏈專案提供，沒有塞入韌體 Git repo。

需還原同層的 RMerlin integration/a3、systemd-lab、a53-runtimes、gcc162-usb、
leon-cgroup 與 multiarch-loader checkpoint。腳本依照現存工作目錄產生绝对路徑，
跨機重建須先還原/重新產生 parent 的 compile/link command manifests，不能把舊
絕對路徑冒充可攜式 SDK。

在已還原依賴、具有本次修改後 `release/src/router/rc` 的工作區執行：

```sh
python3 systemd-upgrade-20260917/scripts/fetch-source.py
python3 systemd-upgrade-20260917/scripts/prepare-sdk.py
python3 systemd-upgrade-20260917/scripts/build-systemd.py
python3 systemd-upgrade-20260917/scripts/stage-systemd.py
python3 systemd-upgrade-20260917/scripts/build-rc.py
python3 systemd-upgrade-20260917/scripts/audit-inputs.py
python3 systemd-upgrade-20260917/scripts/prepare-root.py
python3 systemd-upgrade-20260917/scripts/pack-rehearsal.py --revision systemd257-v5
python3 systemd-upgrade-20260917/scripts/run-qemu.py --label systemd257-v5 --kernel multiarch-loader-20260916/saved-inputs/Image36 --initrd systemd-upgrade-20260917/build/systemd257-v5/guest.cpio.gz --timeout 180
python3 systemd-upgrade-20260917/scripts/run-qemu.py --label services257-v5 --kernel multiarch-loader-20260916/saved-inputs/Image36 --initrd systemd-upgrade-20260917/build/systemd257-v5/guest.cpio.gz --timeout 180 --target services
python3 systemd-upgrade-20260917/scripts/pack.py
```

需要乾淨的 build/output 目錄；部分步驟刻意拒絕覆寫已存在的成品。Meson 1.3.2
重用 compiler option 的問題已有 introspection assertion，調整 compiler flags
應使用新的 build 目錄。QEMU 的失敗開發紀錄保存在 `evidence/development-findings.json`。

來源：
- https://github.com/systemd/systemd/blob/v257.13/README
- https://github.com/systemd/systemd/blob/v258/README
- https://github.com/systemd/systemd/blob/v261/README
