# GT-BE98：繼續拆分 rc 的 mDNS／NTP

基於已通過實機測試的 systemd 257.13、less 704（leon4），將 Avahi 與 NTP 的
程序監督交给 systemd。rc 保留 ASUS 設定產生、WAN 啟停政策與服務事件處理。
這是下一版 leon5 候選，尚未刷入；不能把父版本的實測結果當成本版已通過實機。

`asus-mdns.service` 執行原 Avahi 的 foreground 模式，保留降權、syslog、設定
與 Time Machine／iTunes service XML 更新。USB 子程序將更新請求交回 rc。
`asus-ntpd.service` 執行原 BusyBox NTP，保留兩個時間伺服器、選配 LAN NTP
server、介面限制及同步回呼。同步後的 DDNS、VPN 等工作交由 rc 管理程序執行，
避免重啟 NTP 時誤殺那些服務。細節與測試邊界見 `OWNERSHIP.md`。

rc 三個 C 物件以既有 GCC 15.2、glibc 2.44 的 ARMEL softfp 工具鏈重建，沿用
Cortex-A53、ARMv8-A CRC／crypto 旗標。小型 argv executor 使用 GCC 16.2、
glibc 2.44、`-mcpu=cortex-a53+crc+crypto`、`-Oz`、LTO、RELRO/NOW 及 SHA-1
GNU build ID，在 DGX 原生建置。build ID 是識別碼，不是我們的數位簽章。
保留 a3 的 IPsec 與 HTTPD 修正、完整 less、所有其他使用者空間檔案、核心
#36 與 182 個模組。路由器沒有參與編譯，也沒有在此次工作中改動 live 服務。

## 重現

這是 out-of-tree checkpoint，不是獨立 SDK。Git parent 是
`849ef74df2e6f365234bb3c8f1c62ab2a8f9f526`，候選分支為
`gt-be98-systemd257-services`。需要已還原的同層 less-full、systemd-upgrade、
RMerlin integration/IPsec/HTTPD、systemd-lab、a53-runtimes、gcc162-usb、
leon-cgroup 及 multiarch-loader checkpoints。GCC 工具鏈仍屬獨立專案。

`evidence/external-inputs.json` 列出實際 rc 的來源、header、retained objects 與
libraries 雜湊；私有備份保留它們、建置物件、production rootfs、QEMU 輸入及
候選。父 checkpoint 的 compile/link manifests 使用當時的絕對路徑，跨機還原
必須先重建路徑與 wrapper，不能直接視為可攜式 SDK。先套用本版在
`release/src/router/rc` 的實際原碼，再在乾淨輸出目錄執行：

```sh
python3 systemd-rc-next-20260917/scripts/build-rc.py
python3 systemd-rc-next-20260917/scripts/audit-inputs.py
python3 systemd-rc-next-20260917/scripts/prepare-root.py
python3 systemd-rc-next-20260917/scripts/pack-rehearsal.py --revision network-services-v5
python3 systemd-rc-next-20260917/scripts/run-qemu.py --label network-services-v5 --kernel multiarch-loader-20260916/saved-inputs/Image36 --initrd systemd-rc-next-20260917/build/network-services-v5/guest.cpio.gz --timeout 180
python3 systemd-rc-next-20260917/scripts/run-qemu.py --label network-services-v5-services --kernel multiarch-loader-20260916/saved-inputs/Image36 --initrd systemd-rc-next-20260917/build/network-services-v5/guest.cpio.gz --timeout 180 --target services
python3 systemd-rc-next-20260917/scripts/run-qemu.py --label network-services-v5-new --kernel multiarch-loader-20260916/saved-inputs/Image36 --initrd systemd-rc-next-20260917/build/network-services-v5/guest.cpio.gz --timeout 180 --target network_services
python3 systemd-rc-next-20260917/scripts/pack.py
```

封裝必須同時通過三組相同 initramfs 的測試，並比對 production 的每個檔案、
mode 與 symlink，才會輸出候選。壓縮維持 zstd 22、1 MiB blocks 與 tailends。
使用相同 ELF family／basename 排序，不刪功能，不縮減原 flasher 每個 volume
額外 1 MiB 的保留；總容量上限仍是 734 LEB。封裝後再次解包逐檔比對，並驗證
原 signed bootfs 的簽章及未變動的核心。

## 本版驗證結果

三組 #36／Cortex-A53 離線 QEMU 全部通過，均正常 poweroff、沒有 kernel panic：
完整回歸 107.56 秒；既有 cron／infosvr 32.85 秒；新增 mDNS／NTP 29.46 秒。
涵蓋開機 READY 前啟動、設定更新、NTP LAN listener 開關、mDNS XML refresh、
crash restart、外部程序不被誤殺、非法 argv 檔拒絕、masked unit 不走舊 launcher，
以及 PartOf 停止。另保留三種 ABI、rc 通知、VPN/TLS/DNS、cgroup 與卸載順序回歸。
238 個 rc 外部輸入已逐一雜湊保存，沒有新增 compiler warning 類型。

正式映像 `GT-BE98_leon36-systemd257-mdns-ntpd_zstd22.pkgtb`：

- 90,971,212 bytes，SHA-256 `563fde1342dc1ad71cd55f38c41e389c6c002835dc07899c65fe81849195991f`。
- rootfs 78,553,088 bytes，SHA-256 `d4c853984668552d88d9b260f2faec61e7c171e01b63f0f942daf0278edf254f`。
- 107 + 627 = 734 LEB，與目前版本相同大小；仍保留每 volume 的 1 MiB 額外空間。
- 目前分區配置下，rootfs 還有 12,288 bytes 的餘裕，再多就需要下一個 LEB，
  後續加功能仍需重新量測。

此處的通過只代表離線測試與封裝通過。LAN 實際 multicast discovery、外網 NTP
同步、ASUS 管理介面重啟通知、真實 DDNS/VPN 回呼與硬體加速需刷入後再核對。
目前 live 仍是已驗證的 leon4；本版沒有刷入，也沒有更改 firmware commit 或 rollback。
