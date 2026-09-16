#!/usr/bin/env python3
"""Build modern and real legacy consumers; exercise both libstdc++ string ABIs."""
import json
import os
from pathlib import Path
import shlex
import subprocess

root = Path(__file__).resolve().parents[1]
ws = root.parent
configs = json.loads((root / 'configs/build-targets.json').read_text())
out = root / 'tests/bin'
out.mkdir(exist_ok=True)
records = []
for case in ('armel','armhf','aarch64','armel-legacy','aarch64-legacy'):
    abi = case.replace('-legacy','')
    cfg = configs[abi]
    env = dict(os.environ)
    if cfg['host_library_dir']:
        env['LD_LIBRARY_PATH'] = cfg['host_library_dir']
    obj = root / 'builds' / abi / 'gcc-runtime' / cfg['triplet']
    libgcc, std = obj / 'libgcc', obj / 'libstdc++-v3'
    extra = []
    if case == 'armel-legacy':
        prefix = str(ws / 'github-push-20260915/dependency-sdks/arm32/bin/arm-buildroot-linux-gnueabi-')
        cc,cxx = [prefix+'gcc'],[prefix+'g++']
        env.pop('LD_LIBRARY_PATH',None)
        assert subprocess.check_output(cc+['-dumpfullversion'],env=env,text=True).strip() == '10.3.0'
    elif case == 'aarch64-legacy':
        cc,cxx = ['/usr/bin/gcc-13'],['/usr/bin/g++-13']
    else:
        def driver(name):
            original = shlex.split(Path(cfg[name]).read_text().splitlines()[1])[1:-1]
            return original[:1] + ['-B'+str(libgcc)+'/', '-L'+str(std/'src/.libs'),
                                   '-L'+str(libgcc), '-Wl,-rpath-link,'+str(libgcc)] + original[1:]
        cc,cxx = driver('cc'),driver('cxx')
        source = (ws/'gcc162-usb/gcc-16.2.0' if abi=='aarch64' else root/'sources/gcc-15.2.0')
        extra = ['-nostdinc++','-I'+str(std/'include'/cfg['triplet']),
                 '-I'+str(std/'include'),'-I'+str(source/'libstdc++-v3/libsupc++')]
    flags = cfg['flags'] + ['-O2','-g','-U_TIME_BITS','-U_FILE_OFFSET_BITS',
            '-fexceptions','-funwind-tables','-fno-omit-frame-pointer',
            '-fno-optimize-sibling-calls','-shared-libgcc','-Wl,--build-id=sha1']
    definitions = [
        (cc, [], 'runtime-'+case, ['-std=gnu11',str(root/'tests/runtime-smoke.c'),'-pthread','-ldl','-lgcc_s']),
        (cxx, extra, 'throw-'+case+'.so', ['-std=c++11','-shared','-fPIC','-Wl,-z,defs',str(root/'tests/throw-library.cpp')]),
        (cxx, extra, 'exception-'+case, ['-std=c++11',str(root/'tests/exception-smoke.cpp'),'-pthread','-ldl'])]
    for stringabi in (0,1):
        definitions.append((cxx,extra,'cxx-'+case+'-abi'+str(stringabi),
                            ['-std=c++17','-D_GLIBCXX_USE_CXX11_ABI='+str(stringabi),
                             str(root/'tests/cxx-library-smoke.cpp'),'-pthread','-ldl']))
    for compiler,includes,name,args in definitions:
        mapfile = root / 'evidence' / (name+'.map')
        cmd = compiler + flags + includes + args + ['-Wl,-Map='+str(mapfile),'-o',str(out/name)]
        subprocess.run(cmd,env=env,check=True)
        if '-legacy' not in case:
            link = mapfile.read_text()
            assert str(libgcc/'libgcc_s.so.1') in link, name
            if compiler==cxx:
                assert str(std/'src/.libs/libstdc++.so') in link, name
        records.append(dict(case=case,program=name,command=cmd,
                            old_sdk_used='-legacy' in case,
                            host_library_dir=env.get('LD_LIBRARY_PATH')))
    print('BUILT_PROBES',case,flush=True)
(root/'evidence/probe-builds.json').write_text(json.dumps(records,indent=2)+'\n')
