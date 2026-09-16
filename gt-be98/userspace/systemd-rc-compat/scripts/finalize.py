#!/usr/bin/env python3
"""Pin tested artifacts and explicitly record what hardware integration remains."""
from pathlib import Path
import hashlib,json,re,sys
r=Path(__file__).resolve().parents[1];w=r.parent
from common import inventory,sha
out=r/'build/guarded-final'
qpath=r/'builds/qemu/guarded-final/result.json';q=json.loads(qpath.read_text())
assert q['tests_complete'] and q['guest_complete'] and not q['panic']
assert q['kernel_sha256']=='f6b32cfe97b9e7e2b818fd5aaf5b0a029f52d62dcf086546fd65ebf60c6da3d4'
required={'LAB_RC_MISSING_PRELOAD_REJECTED_PASS','LAB_RC_ORIGINAL_LIBSHARED_SEVEN_APIS_PASS',
    'LAB_RC_RETAINED_OBJECT_WRAPPERS_PASS','LAB_RC_CHILD_FAILURE_ISOLATED_PASS',
    'LAB_RC_REBUILT_BINARY_RELOCATIONS_PASS','LAB_RC_LIBCRYPT_DES_MD5_ABI_PASS',
    'LAB_RC_COMPATIBILITY_ALL_PASS','LAB_RC_ORDERED_DRAIN_PASS'}
assert required<=set(q['lab_lines'])
assert q['lab_lines'].count('LAB_RC_MULTIARCH_PRELOAD_PASS')==3
log=re.sub(r'\x1b\[[0-9;]*[A-Za-z]','',(qpath.parent/'serial.log').read_text())
assert log.rindex('LAB_RC_ORDERED_DRAIN_PASS')>log.index('\nLAB_SYSTEMD_ALL_PASS\n')
assert log.rindex('LAB_RC_ORDERED_DRAIN_PASS')<log.rindex('Unmounting /var')
assert 'All filesystems unmounted.' in log and 'Failed unmounting' not in log
assert sha(out/'guest.cpio.gz')==q['initramfs_sha256']
base=inventory(w/'systemd-lab-20260916/build/guard-service/rootfs');after=inventory(out/'rootfs')
removed=sorted(base.keys()-after.keys());changed=sorted(p for p in base.keys()&after.keys() if base[p]!=after[p])
assert not removed
assert changed==['usr/lib/arm-linux-gnueabi/libcrypt.so.1','usr/libexec/leon-systemd-lab-check','usr/sbin/rc'],changed
modules=[p for p in base if p.endswith('.ko')]
assert len(modules)==182 and all(base[p]==after[p] for p in modules)
assets=json.loads((r/'evidence/runtime-assets.json').read_text())
for name,row in assets['files'].items():assert sha(out/'rootfs'/name)==row['sha256'],name
abi=json.loads((r/'evidence/crypt-abi.json').read_text());assert not abi['missing']
dependencies=json.loads((r/'evidence/dependency-summary.json').read_text())
assert dependencies['all_required_symbols_present']
squash=out/'rootfs.squashfs';size=squash.stat().st_size
blocks=(size+1048576+126975)//126976
report={'status':'rc-compatibility-boundary-qemu-verified','systemd':'255.22',
    'kernel_sha256':q['kernel_sha256'],'kernel_changed':False,'modules_unchanged':len(modules),
    'rc_changed_source_files':26,'source_identity_replacements':119,'source_pid1_signal_replacements':24,
    'source_reboot_replacements':17,'rebuilt_rc_objects':23,'retained_rc_objects':88,
    'shim_abis':['aarch64-linux-gnu','arm-linux-gnueabi','arm-linux-gnueabihf'],
    'rc_compiler':'GCC 15.2.0 / glibc 2.44; A53+CRC+crypto for the 23 rebuilt objects',
    'broker_compiler':'GCC 16.2.0 / glibc 2.44 / cortex-a53+crc+crypto',
    'libcrypt_replacement':'libxcrypt 4.4.38, ARMEL, obsolete ABI enabled; all original exports retained',
    'rootfs_bytes':size,'rootfs_sha256':sha(squash),'guest_sha256':sha(out/'guest.cpio.gz'),
    'delta_vs_manager_lab':size-76587008,'delta_vs_no_adsl':size-74629120,'delta_vs_installed':size-77021184,
    'rootfs_reserved_leb':blocks,'remaining_leb_estimate':734-107-blocks,
    'ubi_estimate_only':True,'qemu_seconds':q['elapsed_seconds'],'qemu_result':str(qpath.relative_to(r)),
    'versioned_dependency_audit':dependencies,'changed_existing_lab_paths':changed,
    'original_libshared_tested':True,'original_libshared_modified':False,
    'real_rc_relocations_checked':True,'real_rc_hardware_initialization_executed':False,
    'shutdown_drains_mock_asus_before_var_unmount':True,'router_modified':False,
    'boot_entry_changed':False,'firmware_commit_performed':False,'flashable_image_created':False,
    'next_step':'Integrate real boot preparation and watchdog/USB readiness, then hardware trial; split services later.'}
(r/'completed.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
