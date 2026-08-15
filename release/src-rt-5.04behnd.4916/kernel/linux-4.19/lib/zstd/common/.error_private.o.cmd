cmd_lib/zstd/common/error_private.o := /opt/toolchains/crosstools-aarch64-gcc-10.3-linux-4.19-glibc-2.32-binutils-2.36.1/usr/bin/aarch64-buildroot-linux-gnu-gcc -Wp,-MD,lib/zstd/common/.error_private.o.d  -nostdinc -isystem /home/docker/am-toolchains/brcm-arm-hnd/crosstools-aarch64-gcc-10.3-linux-4.19-glibc-2.32-binutils-2.36.1/bin.real/../lib/gcc/aarch64-buildroot-linux-gnu/10.3.0/include -I./arch/arm64/include -I./arch/arm64/include/generated  -I./include -I./arch/arm64/include/uapi -I./arch/arm64/include/generated/uapi -I./include/uapi -I./include/generated/uapi -include ./include/linux/kconfig.h -I../../bcmdrivers/opensource/include/bcm963xx/ -I../../bcmdrivers/broadcom/include/bcm963xx -I/build/asuswrt-merlin.ng/release/src-rt-5.04behnd.4916/kernel/bcmkernel/include -I/build/asuswrt-merlin.ng/release/src-rt-5.04behnd.4916/shared/opensource/include/bcm963xx -I/build/asuswrt-merlin.ng/release/src-rt-5.04behnd.4916/kernel/bcmkernel/include/uapi -I/build/asuswrt-merlin.ng/release/src-rt-5.04behnd.4916/kernel/linux-4.19/net/bridge -include ./include/linux/compiler_types.h -D__KERNEL__ -mlittle-endian -Wall -Wundef -Wstrict-prototypes -Wno-trigraphs -fno-strict-aliasing -fno-common -fshort-wchar -Werror-implicit-function-declaration -Werror=return-type -Wno-format-security -std=gnu89 -DGTBE98 -fno-PIE -mgeneral-regs-only -DCONFIG_AS_LSE=1 -fno-asynchronous-unwind-tables -Wno-psabi -mabi=lp64 -fno-delete-null-pointer-checks -Wno-frame-address -Wno-format-truncation -Wno-format-overflow -Wno-int-in-bool-context -Wno-address-of-packed-member -O2 -fno-allow-store-data-races -Wframe-larger-than=2048 -fstack-protector-strong -Wno-unused-but-set-variable -Wno-unused-const-variable -fno-omit-frame-pointer -fno-optimize-sibling-calls -fno-var-tracking-assignments -Wdeclaration-after-statement -Werror=vla -Wno-pointer-sign -Wno-stringop-truncation -Wno-zero-length-bounds -Wno-array-bounds -Wno-stringop-overflow -Wno-restrict -Wno-maybe-uninitialized -fno-strict-overflow -fno-merge-all-constants -fmerge-constants -fno-stack-check -fconserve-stack -Werror=implicit-int -Werror=strict-prototypes -Werror=date-time -Werror=incompatible-pointer-types -Werror=designated-init -fmacro-prefix-map=./= -Wno-packed-not-aligned -DBCA_HNDROUTER -DBCA_CPEROUTER -Wno-array-bounds -Wno-maybe-uninitialized    -DKBUILD_BASENAME='"error_private"' -DKBUILD_MODNAME='"zstd_common"' -c -o lib/zstd/common/error_private.o lib/zstd/common/error_private.c

source_lib/zstd/common/error_private.o := lib/zstd/common/error_private.c

deps_lib/zstd/common/error_private.o := \
  include/linux/kconfig.h \
    $(wildcard include/config/cpu/big/endian.h) \
    $(wildcard include/config/booger.h) \
    $(wildcard include/config/foo.h) \
  include/linux/compiler_types.h \
    $(wildcard include/config/have/arch/compiler/h.h) \
    $(wildcard include/config/bcm/kf/vla/removal/backport.h) \
    $(wildcard include/config/enable/must/check.h) \
    $(wildcard include/config/arch/supports/optimized/inlining.h) \
    $(wildcard include/config/optimize/inlining.h) \
  include/linux/compiler-gcc.h \
    $(wildcard include/config/arm64.h) \
    $(wildcard include/config/retpoline.h) \
    $(wildcard include/config/arch/use/builtin/bswap.h) \
  lib/zstd/common/error_private.h \
  include/linux/zstd_errors.h \
  include/linux/types.h \
    $(wildcard include/config/have/uid16.h) \
    $(wildcard include/config/uid16.h) \
    $(wildcard include/config/lbdaf.h) \
    $(wildcard include/config/arch/dma/addr/t/64bit.h) \
    $(wildcard include/config/phys/addr/t/64bit.h) \
    $(wildcard include/config/64bit.h) \
  include/uapi/linux/types.h \
  arch/arm64/include/generated/uapi/asm/types.h \
  include/uapi/asm-generic/types.h \
  include/asm-generic/int-ll64.h \
  include/uapi/asm-generic/int-ll64.h \
  arch/arm64/include/uapi/asm/bitsperlong.h \
  include/asm-generic/bitsperlong.h \
  include/uapi/asm-generic/bitsperlong.h \
  include/uapi/linux/posix_types.h \
  include/linux/stddef.h \
  include/uapi/linux/stddef.h \
  include/linux/compiler_types.h \
  arch/arm64/include/uapi/asm/posix_types.h \
  include/uapi/asm-generic/posix_types.h \
  lib/zstd/common/compiler.h \
  lib/zstd/common/portability_macros.h \
  lib/zstd/common/debug.h \
  lib/zstd/common/zstd_deps.h \
  include/uapi/linux/limits.h \

lib/zstd/common/error_private.o: $(deps_lib/zstd/common/error_private.o)

$(deps_lib/zstd/common/error_private.o):
