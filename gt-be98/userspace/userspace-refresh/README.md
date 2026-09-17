# GT-BE98 使用者空間盤點與 AArch64 OpenSSL 4 元件

2026-09-17：zstd 的最新正式版仍是 1.5.7，實機 CLI 與函式庫已是此版，
雜湊也與 leon5 候選一致，因此沒有以開發分支取代已驗證的正式版。

本 checkpoint 新建置 OpenSSL 4.0.2 AArch64 元件，已通過指定的上游測試與
原 #36 核心 QEMU 測試。它尚未安裝到路由器，沒有產生可刷的完整韌體。
其他元件的更新清單在 `UPDATES.md`；清單中的版本更新尚未實作。

## OpenSSL 的架構與相依邊界

對 leon5 rootfs 的 955 個 ELF 盤點：664 個 ARM32、291 個 AArch64。
110 個直接連結 libssl/libcrypto 的 ELF 全為 ARM32；AArch64 ELF 也沒有
字面上的 libssl.so/libcrypto.so 載入字串。此檢查不涵蓋動態組合的 dlopen
名稱，亦不能把呼叫命令列工具的行為當成不存在。

因此新增版本放在 `/usr/lib/aarch64-linux-gnu/libcrypto.so.4` 與
`libssl.so.4`，provider 在同架構的 `ossl-modules` 下。
獨立工具為 `/usr/libexec/openssl4`，預設設定目錄為
`/usr/lib/ssl/openssl4`。這五個新增路徑都沒有取代候選中的既有檔案。
SDK 才有未版本化的 linker symlinks；runtime overlay 沒有這些連結。

ASUS 的 ARM32 1.1.1 ABI、我們重建的 ARM32 3.5.8、原 `/usr/sbin/openssl`
與設定均保留。這也保留會呼叫 `openssl` 命令的路徑，例如早期 Dropbear
整合中保留的密碼雜湊 fallback。新庫不會讓現有 ASUS 程式自動變成 64 位元。

OpenSSL 官方當日最新正式版為 4.0.2；4.1.0-alpha1 是預覽版。3.5.8 是
目前 3.5 LTS 修訂，仍適合保留在既有 ARM32 依賴鏈。
來源：[官方下載頁](https://www.openssl-library.org/source/)。

## 建置與測試

- 未修改上游 OpenSSL 4.0.2 原碼；官方 tarball SHA-256 已核對。
- DGX native AArch64：GCC 16.2.0、glibc 2.44、`-mcpu=cortex-a53+crc+crypto`、
  `-O2`、stack protector、RELRO/NOW，具有 GNU SHA-1 build ID。
  build ID 是識別碼，並非數位簽章。
- 上游 OpenSSL 七組測試共 334 項通過，使用目標 glibc 2.44 loader。
  此為選定的 crypto/TLS 測試，並非完整上游測試全集。
- systemd 257.13 的 manager、executor、journald、CLI 與 systemd-creds
  成功直接對 OpenSSL 4.0.2 編譯，沒有修改 systemd 原碼；上游 test-openssl 通過。
  這是相容性 probe，尚未完成 ZSTD/ZLIB/CURL 等正式功能設定。
- `crypto-v2`：原 4.19.294 #36、Cortex-A53 QEMU，沒有 NIC、host disks 或
  hardware passthrough；實際 ARM32 OpenSSL 3.5.8 與 AArch64 4.0.2 同時載入，
  SHA-256、ECDSA 簽章互驗、雙向 TLS 1.3、legacy provider，以及 systemd 257
  host-key credentials 加解密和錯誤名稱拒絕均通過。
- 這不是新的 systemd PID 1 全功能回歸，也不是硬體或完整韌體驗證。

開發紀錄：第一次 Ninja 目標誤寫為 test-openssl-util，已修正為上游的
test-openssl。第一份 VM 測試 machine-id 為 34 個十六進位字元，credentials
正確拒絕；第二份 fixture 使用合法 32 字元。失敗紀錄均保留，沒有修改產品
程式碼來繞過這些測試環境問題。

## 容量結果

完整 overlay 解包後 8,067,736 bytes。把它加入 leon5 後，以同一個 zstd 22、
1 MiB blocks、tailends、family-name 排序重新壓縮：

- 原 rootfs：78,553,088 bytes。
- 加入後：81,633,280 bytes，增加 3,080,192 bytes。
- 保留原有 UBI 每 volume +1 MiB allowance 時，slot1 rootfs 上限為 78,565,376 bytes。
- 超出 3,067,904 bytes，約 2.93 MiB。沒有縮減保留空間或改動 fallback slot。

此數字只加入 OpenSSL 元件，尚未加新版 systemd 功能或其他更新，不能當作
下一版整體大小。整合前需要規劃韌體內容，例如把非開機必要的工具移到使用者
指定的 USB `/usr/local`，或評估實際使用的 OpenSSL runtime 子集；尚未執行這些調整。

## systemd 261 的判斷

保留 257.13。當日上游最新是 261.3，但 v261 最低核心為 5.10，建議 5.14；
258 起也已移除 legacy/hybrid cgroup v1。現有核心 4.19.294 與 Docker v1
資源控制不符合條件。單純更新 glibc/GCC 無法補足核心 API 與 hierarchy 差異。

資料：[v261 README](https://github.com/systemd/systemd/blob/v261/README)、
[v258 NEWS](https://github.com/systemd/systemd/blob/v258/NEWS)、
[257.13](https://github.com/systemd/systemd/releases/tag/v257.13)。

## 重建與依賴

此為 out-of-tree checkpoint，需與 `systemd-upgrade-20260917`、
`systemd-rc-next-20260917`、`systemd-lab-20260916`、`multiarch-loader-20260916`、
`a53-runtimes-20260916`、`gcc162-usb` 等 parent checkpoint 一同還原。
SDK 與固定 OpenSSL tarball 已納入私有備份；工具鏈仍屬於獨立工具鏈專案。
沿用 parent 的已產生 SDK/compiler wrapper，換工作區絕對路徑時須重新產生 wrapper
與 cross file；不能把本目錄單獨 clone 就視為完整 SDK。

在全新 checkpoint 輸出目錄、完成 parent 還原後依序執行：

```sh
python3 userspace-refresh-20260917/scripts/fetch-openssl.py
python3 userspace-refresh-20260917/scripts/audit-elf.py
python3 userspace-refresh-20260917/scripts/build-openssl.py
python3 userspace-refresh-20260917/scripts/stage-openssl.py
python3 userspace-refresh-20260917/scripts/test-openssl.py
python3 userspace-refresh-20260917/scripts/build-systemd-compat.py
python3 userspace-refresh-20260917/scripts/test-systemd-compat.py
python3 userspace-refresh-20260917/scripts/pack-crypto-qemu.py
python3 userspace-refresh-20260917/scripts/run-crypto-qemu.py --label crypto-v2 --kernel multiarch-loader-20260916/saved-inputs/Image36 --initrd userspace-refresh-20260917/build/crypto-qemu-v2/guest.cpio.gz --timeout 180
python3 userspace-refresh-20260917/scripts/measure-size.py
python3 userspace-refresh-20260917/scripts/finalize.py
```

建置與容量脚本拒絕覆寫已存在的成品。實機查詢與上游盤點分別是
`collect-live.py`、`check-upstream.py`；它們不修改路由器。
