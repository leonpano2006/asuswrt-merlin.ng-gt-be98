# GT-BE98 ASUS rc 與 systemd 相容層

2026-09-16。相容層、實際 ARMEL rc 重建、原版 libshared 通知測試與最終 QEMU 關機驗證已完成。這是可繼續整合的開發 checkpoint；尚未接管實機開機，沒有刷機或執行 firmware commit。

## 管理關係

```text
AArch64 systemd，真正 PID 1
  └─ asus-rc.service，Type=notify
      └─ AArch64 leon-rc-broker
          └─ ARMEL rc，以 /sbin/init --leon-systemd 啟動
              └─ 既有 ASUS 硬體／網路／服務流程
```

ASUS rc 先維持一個服務，保留硬體初始化、Runner/RDPA、Wi-Fi、WAN、USB 與 watchdog 的既有呼叫流程。核心仍是原 #36；182 個核心模組的內容、權限與連結均相同。尚未拆成獨立 systemd services，也沒有啟用 networkd 或 udev。

`src/rc-manager.c` 明確記錄 manager 的真實 PID；fork 子程序不能繼承 manager 身分，不偽造 getpid。broker 持有真正的子程序，不以 pidfile 猜測。rc 原先判斷 PID 1 的開源路徑改用這個角色判斷；原 PID 1 啟動分支仍保留。

`src/notify-compat.c` 提供 AArch64、ARMEL、ARMHF 三種 ABI 的通知 shim。glibc 使用 `/usr/$LIB/libleon-rc-notify.so` 選到各自的 multiarch 目錄。七個 notify_rc API 仍呼叫原有 libshared 實作，只在該通知呼叫範圍內將其 `kill(1, SIGUSR1)` 轉到 broker。一般程序訊號保持原行為，原 libshared 位元組不變。broker 缺失時直接回報錯誤，systemd 模式不回落到向 PID 1 發送 ASUS 訊號；shim 缺失時也拒絕啟動 backend。

broker 的 Unix SOCK_SEQPACKET 端點位於 root 專用 `/run/leon-rc`，以 SO_PEERCRED 檢查 UID；HELLO／READY 另檢查必須來自直接子程序。訊息固定大小，僅接受列出的操作及訊號。靜態保留 rc objects 的 kill/reboot 參照由 linker wrap 接上同一邊界；沒有修改 proprietary object。

重啟／關機請求交給 systemd。rc 等待 systemd 開始停止服務，再執行 ASUS 清理；不廣播 kill(-1)，不執行舊的延遲 SysRq 強制重啟。unit 的掛載相依保證 ASUS 清理早於 `/var` 卸載。rc 異常退出會使服務失敗，`Restart=no` 避免未知硬體狀態下反覆初始化。

## 重建內容與必要修正

- `patches/asus-rc-systemd.patch` 包含實際 rc source 修改及 Makefile 接線；`src/` 包含完整新相容程式。
- 修改 26 個 C 檔；GT-BE98 實際重建 23 個 objects，保留並逐一 hash 88 個原 objects。來源中的 119 個角色判斷、24 個 PID 1 訊號與 17 個 reboot 替換包含其他型號條件分支，不能解讀為全部都在此機型執行。
- rc／ARMEL shim 使用 GCC 15.2、glibc 2.44；新 AArch64 broker／工具使用 GCC 16.2、glibc 2.44。新編譯部分指定 Cortex-A53、CRC、crypto；保留的舊 objects 不宣稱已重新最佳化。
- 原 ARMEL libcrypt 引用新 glibc 不再提供的 `__snprintf@GLIBC_PRIVATE`。重建 libxcrypt 4.4.38 並啟用 obsolete ABI，原有 export 的名稱及版本全部保留；DES／MD5 crypt 向量通過。上游來源 hash 記錄於相依資料。
- runtime ELF 記錄 SHA-256、GNU Build ID、compiler flags 與 DT_NEEDED；Build ID 是建置識別，不是密碼學簽章。

ARMEL flags 為 `-mcpu=cortex-a53+crypto -march=armv8-a+crc+crypto -mfpu=crypto-neon-fp-armv8 -mfloat-abi=softfp`；AArch64 為 `-mcpu=cortex-a53+crc+crypto`。全部在 DGX 建置，沒有使用路由器編譯。

## 驗證結果

最終測試為 `builds/qemu/guarded-final`，16.82 秒，正常 power down、無 panic。測到的範圍包括：

- 原 #36 核心啟動 systemd PID 1、journald、service 管理、cgroup v1 memory/pids/delegation 與 daemon-reexec。
- 三種 ABI 的 `$LIB` preload；真實 getpid 不變；缺 broker／缺 preload 會拒絕執行。
- **原版 ARMEL libshared 的全部七個通知 API**，配合僅 RAM 的 NVRAM 測試 provider。
- 未授權 peer／HELLO／READY、未知操作與禁止訊號的拒絕；對其他程序的訊號不變。
- rc manager 角色、subreaper 回收雙 fork 子程序、靜態 linker wrappers，以及 tmp/etc/mount 保留行為。
- readiness、start/stop/restart、反覆正常起停；故意終止 backend 後 unit 失敗而 systemd 保持運作，沒有自動重啟。
- 真正 ARMEL trial guard 在被管理的子程序中仍攔截測試 provider 的 metadata 寫入，未接觸 NAND。
- 實際重建 rc 的 37 個 DT_NEEDED 及動態符號 relocation 均解析成功，不含 host 絕對 library 路徑。
- rc 提出 poweroff，由真實 broker 呼叫 systemctl；模擬 ASUS backend 完成清理後才卸載 `/var`，最後全部檔案系統卸載成功。

版本化相依稽核涵蓋 766 個 consumers、43 個 providers，包含 70 個 libgcc、2 個 libstdc++ consumers。此靜態稽核略過 GLIBC_PRIVATE；實際 rc 另以 loader 完整檢查 relocation，並對替換的 libcrypt 驗證 export ABI，不能擴大解讀為所有二進位的所有執行路徑皆已測試。

QEMU 沒有 Broadcom 硬體，因此 **沒有執行真實 rc 的硬體初始化**。mock backend 驗證的是實際連入 rc 的相容 helper 與管理契約，不能據此宣稱 Runner 吞吐、無線或真實關機已驗證。

## 空間與下一步

測試 rootfs 使用 zstd 22、1 MiB block、tailends，共 **76,787,712 bytes**。比上一個 systemd manager 原型增加 **200,704 bytes（196 KiB）**，仍比前次安裝版 rootfs 小 **233,472 bytes（228 KiB）**。依上次分區資料估計，bootfs 保留 107 LEB、rootfs 需 613 LEB，尚餘 14 LEB；正式 pkgtb 仍須重新核對當時分區與映像大小。

rootfs SHA-256：`b19dce76472ec8a2cadc4d522f7b36d9ab50cec50657f8ac74d1d5a7558b6466`

initramfs SHA-256：`73fb53f2c3d50559a4845d7e123d4749b6ee67b9b0656912bd57272cb55860fe`

下一步是整合開機前置設定、USB/JFFS 就緒與 watchdog，再安排實機 trial。unit 尚未 enable，init 入口未替換，試開機與 rollback 機制未改。確認這層在實機成立後，才逐步把低耦合服務交給 systemd；硬體／加速器依賴鏈仍需保留順序。

systemd 255.22 沿用前一相容性原型基準，正式版的維護修補及安全組態仍待整合。核心 FHANDLE、deprecated sysfs／完整 udev 的限制也未由本次解決。

## 重現與保存

腳本預期位於 workspace 下的 `systemd-rc-compat-20260916`；GitHub 的 userspace 子目錄是相同程式碼的保存位置，重建前需依此 checkpoint 名稱放回 workspace。依賴 `systemd-lab-20260916`、`a53-runtimes-20260916`、原 ASUS／BSP source snapshot 和先前工具鏈備份，詳見 `evidence/build-dependencies.json`。

`sources/rc` 保存完整 rc source 與原 objects。`evidence/rc-include-inputs.json` 由相同編譯命令的 `-M` 產生；實際使用的 BSP headers／設定內容另存 `saved-inputs/workspace`，避免只留文件卻丟掉建置輸入。此資料只備份到自己的 ML350，不上傳原 proprietary objects 到 GitHub。

在已恢復依賴的新工作目錄執行下列流程；先建立 checkpoint 的 build/evidence/configs/sources/patches/overlay 目錄。libxcrypt source 的 configure 由前一 systemd-lab 的 build-deps 流程產生。prepare-rc、pack-guest 拒絕覆寫既有產物。

```sh
python3 systemd-rc-compat-20260916/scripts/capture-build-flags.py
python3 systemd-rc-compat-20260916/scripts/prepare-rc.py
python3 systemd-rc-compat-20260916/scripts/build-bridge.py
python3 systemd-rc-compat-20260916/scripts/build-crypt.py
python3 systemd-rc-compat-20260916/scripts/audit-crypt-abi.py
python3 systemd-rc-compat-20260916/scripts/build-rc.py
python3 systemd-rc-compat-20260916/scripts/build-probes.py
python3 systemd-rc-compat-20260916/scripts/stage.py
python3 systemd-rc-compat-20260916/scripts/pack-guest.py --revision guarded-final --level 22
python3 systemd-rc-compat-20260916/scripts/run-qemu.py --label guarded-final --kernel multiarch-loader-20260916/saved-inputs/Image36 --initrd systemd-rc-compat-20260916/build/guarded-final/guest.cpio.gz --timeout 120
python3 a53-runtimes-20260916/scripts/audit-dependencies.py --rootfs systemd-rc-compat-20260916/build/guarded-final/rootfs --report systemd-rc-compat-20260916/evidence/full-rootfs-dependencies.json > systemd-rc-compat-20260916/evidence/dependency-summary.json
python3 systemd-rc-compat-20260916/scripts/finalize.py
python3 systemd-rc-compat-20260916/scripts/snapshot-dependencies.py
python3 systemd-rc-compat-20260916/scripts/make-backup.py
```

搬到新的絕對路徑時，重新產生 compiler wrappers 和 parent flags；不要直接沿用記錄中舊的 workspace 路徑。只重跑保存的 guest 則不需要編譯器，換一個 QEMU `--label` 即可。備份以 tar 保留權限與 symlink，逐檔驗證 hash；本地與 ML350 收件結果分別記錄於 backup-receipt.json、ml350-backup-receipt.json。大檔僅保存最終 guest/rootfs，之前失敗測試只保留小型日誌。
