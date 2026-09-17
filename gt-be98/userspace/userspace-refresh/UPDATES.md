# 使用者空間正式版更新盤點（2026-09-17）

版本來自實機查詢、建置來源紀錄與官方 release/index。這是更新候選清單，
除新增且尚未部署的 AArch64 OpenSSL 4 元件外，本次沒有更新下列表格中的程式。
CLI 更新也不等於替換 ASUS 所連結的 shared library。

| 元件 | 目前版本 | 官方新版 | 處理 |
|---|---|---|---|
| jq | 來源 1.7.1；實機顯示 `jq-` | [1.8.2](https://github.com/jqlang/jq/releases/tag/jq-1.8.2) | 優先更新 native CLI，修復版本標記；保留 ASUS 腳本相容性 |
| SQLite CLI | 3.42.0 | [3.53.4](https://sqlite.org/changes.html) | 優先重建 native CLI；不連帶替換 ASUS SQLite library |
| socat | 1.7.3.2 | [1.8.1.3](http://www.dest-unreach.org/socat/) | 重建 native 工具並重新核對現有功能；官方 HTTPS 憑證驗證失敗，此版號由官方 HTTP 頁確認 |
| curl/libcurl | ARM32 8.17.0、OpenSSL 1.1.1w | [8.22.0](https://curl.se/download.html) | 優先新增 AArch64 依賴供 systemd；既有 ARM32 BSP 版本需另核對 patch/ABI |
| Bash | 5.3 patch 15 | [patch 20](https://ftp.gnu.org/gnu/bash/bash-5.3-patches/) | 套用 16–20 並測 shell 行為 |
| GNU coreutils | 9.11 | [9.12](https://ftp.gnu.org/gnu/coreutils/) | 更新 `/usr/gnu/bin` 的同一套 multicall/連結配置 |
| util-linux/native libs | 2.42.2 | [2.42.3](https://mirrors.edge.kernel.org/pub/linux/utils/util-linux/v2.42/) | 工具、libmount/libblkid/libuuid 一起核對；測舊核心 fallback |
| OpenSSH sftp-server | 建置來源 10.2p1 | [10.5p1](https://www.openssh.com/releasenotes.html) | 更新獨立 sftp-server，保留 Dropbear SSH 整合；沒有安裝完整 sshd |
| Docker | 29.8.0 | [29.8.1](https://github.com/moby/moby/releases/tag/docker-v29.8.1) | 可排後；此修訂主要修 containerd image store 的 docker load dangling image 問題 |
| GCC 15/ARMEL runtimes | 15.2.0 | [15.3](https://gcc.gnu.org/releases.html) | 後續在獨立工具鏈專案處理；libgcc/libstdc++ 需 ABI 與符號回歸 |
| dnsmasq64 舊測試副本 | 2.93-test2 | [2.93](https://thekelleys.org.uk/dnsmasq/CHANGELOG) | 舊副本需要整理；正式 `/usr/sbin/dnsmasq` 已是 2.93 |

以下正式版沒有發現更新，保留：

| 元件 | 目前／最新正式版 | 官方來源 |
|---|---|---|
| zstd | 1.5.7 | [release](https://github.com/facebook/zstd/releases/tag/v1.5.7) |
| zlib | 1.3.2 | [release](https://github.com/madler/zlib/releases/tag/v1.3.2) |
| nano | 9.2 | [news](https://www.nano-editor.org/news.php) |
| htop | 3.5.3 | [release](https://github.com/htop-dev/htop/releases/tag/3.5.3) |
| iperf3 | 3.21 | [release](https://github.com/esnet/iperf/releases/tag/3.21) |
| Dropbear | 2026.94 | [changes](https://matt.ucc.asn.au/dropbear/CHANGES) |
| less | 704 | [download](https://www.greenwoodsoftware.com/less/download.html)，710 是 beta |
| GNU findutils | 4.11.0 | [releases](https://ftp.gnu.org/gnu/findutils/) |
| btrfs-progs | 7.1 | [release](https://github.com/kdave/btrfs-progs/releases/tag/v7.1) |
| xfsprogs | 7.1.1 | [releases](https://mirrors.edge.kernel.org/pub/linux/utils/fs/xfs/xfsprogs/) |
| OpenVPN | 2.7.7 | [release](https://github.com/OpenVPN/openvpn/releases/tag/v2.7.7) |
| OpenSSL ARM32 3.5 LTS | 3.5.8 | [downloads](https://www.openssl-library.org/source/) |
| systemd 257 維護線 | 257.13 | [release](https://github.com/systemd/systemd/releases/tag/v257.13) |
| native GCC | 16.2.0 | [releases](https://gcc.gnu.org/releases.html) |

範圍：先前自建的主要工具與相關執行期，不是對全部 ASUS/Broadcom 私有檔案、
每個相依庫、開發分支 commit 或容器內套件做完整漏洞盤點。zstd 官方 dev 分支
有後續 commit，但還沒有比 1.5.7 新的正式版。
