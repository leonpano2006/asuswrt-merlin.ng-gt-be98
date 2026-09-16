# GT-BE98：移除閒置 ADSL PHY 韌體的候選

2026-09-16。此候選已完成離線驗證，尚未刷入或 commit；本次沒有連線修改路由器。

## 判定與範圍

只移除 `/rom/etc/adsl1/adsl_phy.bin`，原始大小 1,162,836 bytes，SHA-256：
`bea8e7fdd61d00ed7ad51054cddcfaea264c0247359f2181ecd02bdf44580011`。

- [ASUS GT-BE98 官方規格](https://rog.asus.com/networking/rog-rapture-gt-be98-model/spec/)列出 Ethernet WAN/LAN 與 USB，沒有 DSL/RJ11 線路接口。
- 已部署的 #36 核心設定關閉 `CONFIG_BCM_ADSL`、`CONFIG_BCM_XTMCFG`、`CONFIG_BCM_XTMRT`；ASUS 使用者空間設定關閉 DSL/VDSL。
- 相同 SHA 的韌體檔存在 SDK `targets/96813GW/fs` 與 `fs.install` 樣板中。
- 掃描其餘 3,482 個一般檔案（包括程式、函式庫、模組、腳本）與解壓後核心，沒有找到此檔名或 `/etc/adsl1` 的引用，也沒有 `xdslctl`、`adsldd` 字串。兩個 `adsl1` 命中只是通用 `bcmadsl1` 裝置節點定義。
- `CONFIG_BCM_DSL_XRDP=y` 與 `BUILD_DSL_RUNNER=y` 涉及此平台的 Runner 路徑，完整保留。`RTCONFIG_DSLITE=y` 的 IPv4-over-IPv6 功能也保留，並非 ADSL 實體層。

證據：`evidence/adsl-audit.json`、`evidence/sdk-excerpts.json`、`configs/`。
靜態引用掃描本身不能證明所有動態產生的路徑都不存在；結論同時依據硬體接口、核心/使用者空間設定與安裝內容。

## 成品與容量

候選：`candidate/GT-BE98_leon36-a53-runtimes_no-adsl_zstd22-1m-tailends.pkgtb`

| 項目 | bytes |
| --- | ---: |
| 目前安裝版 rootfs | 77,021,184 |
| 前一個僅改壓縮的候選 rootfs | 75,309,056 |
| 本候選 rootfs | 74,629,120 |
| 本次 ADSL 移除額外節省 | 679,936（664 KiB） |
| 與目前安裝版合計差額 | 2,392,064（2.28125 MiB） |
| 本候選完整 pkgtb | 87,047,244 |

pkgtb SHA-256：`4c280ec6dd8620e86e4d3dbad6e9b29ee0a3ea325cae6f31326b5d43981cdcb0`

rootfs SHA-256：`14c5186e30974498079f6edc59bdaed02e8bafed590c9d663d688b3def673e1f`

使用 SquashFS zstd level 22、1 MiB block、tailends，固定原始建立時間；`mksquashfs` 的 level 22 不需要獨立 `zstd` CLI 的 `--ultra` 開關。

依既有 UBI 容量觀察及每個韌體 volume 額外 1 MiB 的配置規則，bootfs/rootfs 需 107/596 個 LEB；若以本候選替換 slot 1，可剩 31 個 LEB（3.75390625 MiB），目前為 12 個。此為離線估算，實際刷入前應重新核對 slot 與容量。沒有改動 UBI 配置或回退分區。

## 驗證

- 從候選重新解包，比對完整清單，只有指定檔案被刪除；其餘路徑的內容、模式、符號連結與時間戳一致。保留原本的空目錄與其時間戳。
- 全部 182 個 `.ko`、Wi-Fi/Runner/RDPA 相關檔案與既有使用者空間改動原樣保留。
- 已簽署 bootfs 位元組完全相同，RSA-PSS 簽名通過；核心仍為原 #36，SHA-256 `f6b32cfe97b9e7e2b818fd5aaf5b0a029f52d62dcf086546fd65ebf60c6da3d4`。
- 精確 #36 核心於 Cortex-A53 QEMU 掛載候選，讀取並雜湊全部 3,482 個檔案，確認 ADSL 檔案不存在；無 panic，完成標記成功，29.66 秒。
- 312 個無快取與 312 個有快取的動態連結檢查通過；三種 glibc ABI、GCC/C++ runtime、舊插件、usr-merge 模組路徑與 PID 1 trial guard 測試通過。

QEMU 沒有 Broadcom 真實硬體與 NAND；它不能驗證實機 Runner 吞吐量或實際開機時間。測試中缺少 `ubi:data` 的訊息來自模擬器沒有對應 UBI 裝置，與刪除 ADSL 檔案無關。完整結果在 `builds/qemu/no-adsl-zstd22-1m-tailends/`。

## 重建

所有命令在工作區根目錄執行。原映像與輸入以 SHA-256 固定；使用 `unsquashfs`、`mksquashfs`、`qemu-system-aarch64`、OpenSSL、lzop、Python 3 與 pyelftools。建置在主機執行，沒有使用路由器編譯。

```sh
python3 rootfs-no-adsl-20260916/scripts/audit-adsl.py
python3 rootfs-no-adsl-20260916/scripts/build-rootfs.py
python3 rootfs-no-adsl-20260916/scripts/prepare-qemu.py
python3 rootfs-no-adsl-20260916/scripts/run-qemu.py --label no-adsl-zstd22-1m-tailends --kernel multiarch-loader-20260916/saved-inputs/Image36 --initrd rootfs-no-adsl-20260916/build/guest.cpio.gz --timeout 180 --complete-marker QEMU_USRMERGE_COMPLETE
python3 rootfs-no-adsl-20260916/scripts/finalize-candidate.py
```

建置與打包脚本會拒絕覆寫已存在的成品；重現時使用新的工作目錄或先將既有產物移到另一處。若從備份復原，先解開備份至空目錄，再將保存的 `a53-runtimes-20260916/build/rootfs.squashfs` 以 `unsquashfs` 解至同目錄下的 `unpacked-rootfs`。保留其 metadata；重建原有 `build` 與 `candidate` 產物時先移走這兩個目錄中的生成檔。

這是獨立的最後 rootfs 階段修改。原 SDK 與已驗證的前版成品未修改；未來從 ASUS 樹重新產生 rootfs 時，應保留這個精確的單檔移除步驟，並在輸入變更後重新驗證，不能用 `*dsl*` 廣泛刪除。

備份腳本 `scripts/make-backup.py` 收錄實作、設定、證據、候選、QEMU 輸入與原始映像，不只 Markdown。ML350 預定位置為 `/home/leonpano/amng-out/rootfs-no-adsl-20260916/`；實際傳輸與雜湊核對收據另存於 `ml350-backup-receipt.json`。
