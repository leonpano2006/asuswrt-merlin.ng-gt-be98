# GT-BE98：RMerlin 102.9 使用者空間整合候選

已直接整合 RMerlin `96831be75b3b891f6aa4c608f00cc7bb2d499d67`（3006.102.9-beta1），保留 GT-BE98 機種支援與先前的 Leon 使用者空間改造。父版本是自有分支 `15ee3e5f0cf462e2d54a6c7b23117d9936263e59`，共同祖先為 `542f71114524e009773c124a89f438d53be1c6f5`。不依賴 gnuton 發布這一輪更新；GitHub 的 fork 歸屬和既有歷史沒有重寫。

這是**已完成建置、離線測試與打包的候選**，尚未刷入實機，沒有 firmware commit。Git 原碼提交與路由器的 firmware commit 是兩回事。

## 已納入

| 部分 | 實際候選內容 |
|---|---|
| TLS | OpenSSL 3.5.8：新 CLI、OpenVPN、Tor、IPsec 使用；舊 BSP 依賴保留真正的 OpenSSL 1.1.1 |
| VPN | OpenVPN 2.7.7、EasyRSA 3、tls-crypt-v2、strongSwan 6.0.4、對應 libovpn 與 WebUI |
| 網路服務 | dnsmasq 2.93（保留 Nettle DNSSEC）、miniupnpd 2.3.11／IGDv2、inadyn 上游修正 |
| 其他 | Tor 0.4.9.11、haveged 1.9.22、amtm 啟動腳本、CA bundle、管理頁面及字典 |
| 管理服務 | shared、rc、httpd、infosvr 依新的可用原碼重建；保留指定 GT-BE98 預編譯物件 |
| 既有 Leon 改造 | glibc 2.44、A53 runtimes、usrmerge／multiarch、systemd PID 1、rc broker、notify 相容層、haveged unit、NVRAM 快取修補 |

上游 QoS／HW AQM 原碼和頁面已納入，但沒有在實機啟用或聲稱已驗證硬體 AQM。四個 radio、flow cache／runner、WAN、VPN 實際連線仍需要下一階段實機試開機確認。

## 編譯與相依性

所有新目標 ELF 均在 DGX 執行 AArch64 主機版 GCC 15.2，交叉編譯為 **ARMEL softfp**，使用 glibc 2.44 sysroot。ARM32 旗標為 `-mcpu=cortex-a53+crypto -march=armv8-a+crc+crypto -mfpu=crypto-neon-fp-armv8 -mfloat-abi=softfp`。前處理器實測 ARMv8、CRC32、crypto、NEON 均啟用，見 `evidence/isa-macros.json`。這一輪沒有更換既有 AArch64 GCC 16.2 runtime，也沒有在路由器編譯。

73 個重建 ELF 均有 GNU SHA-1 Build ID 和 GCC 旗標紀錄。管理服務使用 142 個可編譯原碼輸入，以及 70 個指定機種的預編譯物件；451 個標頭／原碼依賴已記錄雜湊。建置腳本依組件 Makefile 選取物件，包括優先保留 bcmutils／bcmwifi_channels／bcmxtlv 的 model prebuild，並保留 rc 的 `--gc-sections` 和 systemd 包装選項。沒有用絕對主機路徑作為 DT_NEEDED，亦無主機 RPATH 留在候選中。

OpenSSL 3.5 不能直接取代此 GT-BE98 BSP 的 1.1 庫。逐一檢查既有映像的 165 個直接 TLS 相依檔案，發現 49 個使用上游 shim 未輸出的符號，包含無線元件。因此沒有安裝該 shim，也沒有改寫 blob。rc／httpd／libovpn／infosvr／inadyn 及其封閉依賴維持 1.1 ABI；OpenVPN、Tor、IPsec 和 openssl CLI 的依賴鏈使用 3.5。新庫放在 `/usr/lib/arm-linux-gnueabi`，沒有製造一排 `/usr/lib` 相容連結。

新 GPL 的四個私有介面不在現有 GT-BE98 BSP：`wl_scb`、`ed_thresh_clear`、`init_asus_pp_eula`、`backup_eth_ob_log`。以 GTBE98 編譯條件保留原有機種行為，沒有製造假成功的函式。舊的同意條款處理仍在。新的私有 shell wrapper 呼叫改用既有 `eval()` 的參數陣列執行 wl／dns_ping；另外修正兩個 `open(O_CREAT)` 遺漏 mode 的原碼錯誤。

核心仍是已驗證的 **#36 / Linux 4.19.294**，182 個模組全部逐檔相同；bootfs、kernel、loader 和 fallback 政策沒有更換。整合樹中的新上游 SDK／RTL8372／kernel 變更不等於本候選已採用它們。重播建置明確沿用 parent checkpoint 的核心與 BSP，避免混用新版 GT-BE98_PRO blobs。

## 驗證與映像

最終 `upstream-v6` QEMU 回歸在 107.15 秒內通過，使用實際 #36 核心、production early init 與候選 rootfs。涵蓋 systemd PID 1、三 ABI preload、cgroup memory/pids delegation、rc 訊號／角色路由、失敗隔離、haveged 單一管理者、OpenVPN 角色判斷、實際 ELF relocation 與依序卸載關機。

另實測 OpenSSL 3.5 TLS 1.3 server 與原 1.1 client 互通、憑證驗證、OpenVPN AES-256-GCM 自測與 tls-crypt-v2、dnsmasq loopback DNS 查詢、Tor 設定驗證、IPsec 版本載入及 EasyRSA 3 目錄初始化。QEMU 的 ASUS 硬體服務以測試 backend 替代，因此不代表無線／交換器／加速器已通過實機測試。

候選：`GT-BE98_leon36-rmerlin1029a1_zstd22.pkgtb`

- 映像 **90,840,140 bytes（86.632 MiB）**；rootfs **78,422,016 bytes**。
- SHA-256：`c75e68f6c860b240a93326fef1f8049e8fee5ba3c9c73c215a99cd8ba6d87ee9`。
- SquashFS：zstd **22**、1 MiB block、tailends，按檔案類型／ELF 架構與大小排序。先前超額的映像沒有輸出可刷檔案；最後的排序改變儲存位置，沒有刪除功能或更改檔案内容。
- 解包後的檔案內容、權限、連結與實測 production tree 完全一致。原 signed bootfs 的簽章驗證通過，其他 FIT payload 逐位元組相同。
- UBI 配置預算 **734 LEB**；候選預留 bootfs 107 + rootfs 626 = **733 LEB**。此計算已替每個 payload 加 1 MiB；預算外剩 **1 LEB**，後續再加功能需要重新處理容量。
- 本輪只讀實機確認：目前 booted First、normal reboot Second、commit flags `0/1`；slot2 回退保留，沒有寫入路由器。

## 重播建置

這個 fork 的完整映像由已保存的 parent rootfs／BSP 加上此輪重建結果組成。不可用通用的 OpenSSL 3.5 + shim 配方直接產生 GT-BE98 映像；router Makefile 會對該組合明確報錯。`LEON_GTBE98_SPLIT_TLS_REPLAY=1` 僅供脚本讀取 Makefile 配方，不能當成讓通用映像相容的開關。

從已還原的 DGX workspace（含先前 checkpoint、GCC/sysroot、原 BSP）執行：

```sh
python3 gt-be98/userspace/rmerlin-upstream/scripts/replay.py \
  --workspace /path/to/verified-workspace \
  --repo /path/to/this-git-checkout \
  --webui-tar /path/to/webui-output.tar \
  --output /path/to/verified-workspace/rmerlin-replay
```

先加 `--check-inputs` 可核對 parent inventory、kernel、toolchain 設定、WebUI 雜湊與 source ancestry。需原生 gperf、autotools、Python pyelftools、QEMU、SquashFS zstd 工具。WebUI archive 是由 `build-webui-remote.py` 在 ML350 隔離目錄使用 ASUS x86 字典工具產生，和該版頁面一起校驗，不能混用其他版本的字典。

重播入口的輸入檢查已通過；本輪各組件建置、staging、QEMU 與包裝均實際執行。没有另跑第二次完整從零的 replay。GCC 工具鏈仍由既有獨立 repo／workspace 管理，沒有把工具鏈二進位檔塞入韌體原碼 repo。

`evidence/reviewed-source-overlay.json` 列出 44 個實際原碼更動；這些修改直接提交在 `release/`，不只有本文件。`scripts/`、`src/`、`tests/`、`configs/` 和建置／QEMU／包裝證據與原碼一起保存。完整候選、WebUI archive、建置輸出和必要依賴快照另存 DGX／ML350 checkpoint archive。
