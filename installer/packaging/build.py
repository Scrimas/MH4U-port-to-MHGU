"""build.py : the installer's release files into installer/dist/ (MHGU_Editor's app/packaging/build.sh, in Python: the
repo has no shell scripts):
  MHGU-Definitive-Edition-Installer-<v>-x86_64.exe        Windows 10/11, mingw-w64 cross build, one file
  MHGU-Definitive-Edition-Installer-<v>-arm64.exe         Windows 11 on ARM, llvm-mingw cross build, one file
  MHGU-Definitive-Edition-Installer-<v>-x86_64.AppImage   Linux, glibc 2.28 (cargo-zigbuild), AppImage type 2 runtime
  MHGU-Definitive-Edition-Installer-<v>-arm64.AppImage    Linux on ARM (aarch64), the same
  SHA256SUMS-<v>                            the files' sha256 (the installer's self-update checks them)

  python3 installer/packaging/build.py [--exe | --appimage] [--arch x86_64 | --arch arm64]

Needs:
  x86_64 .exe       rustup target x86_64-pc-windows-gnu + mingw-w64-gcc
  arm64 .exe        rustup target aarch64-pc-windows-gnullvm + LLVM_MINGW=<an llvm-mingw folder> (its bin/ is put on
                    PATH for this build only: clang, lld, llvm-ar, aarch64-w64-mingw32-windres; ring needs clang for
                    Windows on ARM)
  x86_64 AppImage   cargo-zigbuild + zig (else the binary needs this machine's glibc or newer), mksquashfs
                    (squashfs-tools), APPIMAGE_RUNTIME=<the type 2 runtime-x86_64 file>
  arm64 AppImage    rustup target aarch64-unknown-linux-gnu + cargo-zigbuild + zig (zig needed unless this machine is
                    aarch64), mksquashfs, APPIMAGE_RUNTIME_ARM64=<the type 2 runtime-aarch64 file>; fontconfig is
                    loaded at start (gui/Cargo.toml: fontique fontconfig-dlopen on aarch64 Linux, there is no
                    aarch64 libfontconfig to link against when cross building), as Wayland and xkbcommon already are
CI: .github/workflows/installer.yml, in an Arch Linux container like the editor's.
"""
import hashlib, os, platform, shutil, subprocess, sys, tempfile, tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
INST = os.path.dirname(HERE)
DIST = os.path.join(INST, 'dist')
NAME = 'MHGU-Definitive-Edition-Installer'
ARCHS = ('x86_64', 'arm64')            # the file names' arch (installer/core/src/selfupdate.rs ARCH)
EXE_TARGET = {'x86_64': 'x86_64-pc-windows-gnu', 'arm64': 'aarch64-pc-windows-gnullvm'}
LINUX_TARGET = {'x86_64': 'x86_64-unknown-linux-gnu', 'arm64': 'aarch64-unknown-linux-gnu'}
RUNTIME_ENV = {'x86_64': 'APPIMAGE_RUNTIME', 'arm64': 'APPIMAGE_RUNTIME_ARM64'}


def run(*a, env=None):
    print('$', ' '.join(a), flush=True)
    subprocess.run(a, cwd=INST, check=True, env=env)


def has(cmd):
    return shutil.which(cmd) is not None


def host_arch():
    return {'x86_64': 'x86_64', 'amd64': 'x86_64', 'aarch64': 'arm64', 'arm64': 'arm64'}.get(platform.machine().lower())


def exe(ver, arch):
    target, env = EXE_TARGET[arch], None
    if arch == 'arm64':
        lm = os.environ.get('LLVM_MINGW')
        if not lm or not os.path.isfile(os.path.join(lm, 'bin', 'aarch64-w64-mingw32-clang')):
            sys.exit('the arm64 .exe needs LLVM_MINGW=<an llvm-mingw folder> (bin/aarch64-w64-mingw32-clang)')
        # llvm-mingw only for this build: its x86_64-w64-mingw32-* would replace mingw-w64-gcc in the x86_64 one
        env = dict(os.environ, PATH=os.path.join(lm, 'bin') + os.pathsep + os.environ.get('PATH', ''))
        cc = os.path.join(lm, 'bin', 'aarch64-w64-mingw32-clang')
        env.setdefault('CARGO_TARGET_AARCH64_PC_WINDOWS_GNULLVM_LINKER', cc)
        env.setdefault('CC_aarch64_pc_windows_gnullvm', cc)
        env.setdefault('AR_aarch64_pc_windows_gnullvm', os.path.join(lm, 'bin', 'llvm-ar'))
        # winresource runs a bare llvm-windres for a gnullvm target: x64 resources, which lld refuses in an arm64
        # .exe; the prefixed one takes its target from its name
        env.setdefault('WINDRES', os.path.join(lm, 'bin', 'aarch64-w64-mingw32-windres'))
        # gnullvm links Rust's unwinder as libunwind.dll (llvm-mingw's, not on Windows: the .exe would not start)
        # unless crt-static (library/unwind/src/lib.rs): libunwind.a goes into the .exe, one file as the x86_64 one
        env.setdefault('CARGO_TARGET_AARCH64_PC_WINDOWS_GNULLVM_RUSTFLAGS', '-C target-feature=+crt-static')
    run('cargo', 'build', '--release', '--locked', '-p', 'mhgu-de-installer', '--target', target, env=env)
    out = os.path.join(DIST, '%s-%s-%s.exe' % (NAME, ver, arch))
    shutil.copy(os.path.join(INST, 'target', target, 'release', 'mhgu-de-installer.exe'), out)
    return out


def appimage(ver, arch):
    target = LINUX_TARGET[arch]
    if has('zig') and subprocess.run(['cargo', 'zigbuild', '--help'], capture_output=True).returncode == 0:
        run('cargo', 'zigbuild', '--release', '--locked', '-p', 'mhgu-de-installer', '--target', target + '.2.28')
        binary = os.path.join(INST, 'target', target, 'release', 'mhgu-de-installer')
    elif arch == host_arch():
        print('   (cargo-zigbuild not found: linking against this machine\'s glibc)')
        run('cargo', 'build', '--release', '--locked', '-p', 'mhgu-de-installer')
        binary = os.path.join(INST, 'target/release/mhgu-de-installer')
    else:
        sys.exit('the %s AppImage needs cargo-zigbuild and zig on this %s machine' % (arch, host_arch()))
    runtime = os.environ.get(RUNTIME_ENV[arch])
    if not runtime or not os.path.isfile(runtime) or not has('mksquashfs'):
        sys.exit('the %s AppImage needs %s=<type 2 runtime> and mksquashfs' % (arch, RUNTIME_ENV[arch]))
    with tempfile.TemporaryDirectory() as tmp:
        app = os.path.join(tmp, 'AppDir')
        for d in ('usr/bin', 'usr/share/applications', 'usr/share/icons/hicolor/256x256/apps'):
            os.makedirs(os.path.join(app, d))
        shutil.copy(binary, os.path.join(app, 'usr/bin/mhgu-de-installer'))
        desktop = os.path.join(HERE, 'mhgu-de-installer.desktop')
        icon = os.path.join(INST, 'gui/assets/icon-256.png')
        shutil.copy(desktop, os.path.join(app, 'usr/share/applications'))
        shutil.copy(desktop, app)
        shutil.copy(icon, os.path.join(app, 'usr/share/icons/hicolor/256x256/apps/mhgu-de-installer.png'))
        shutil.copy(icon, os.path.join(app, 'mhgu-de-installer.png'))
        os.symlink('mhgu-de-installer.png', os.path.join(app, '.DirIcon'))
        with open(os.path.join(app, 'AppRun'), 'w', newline='\n') as f:
            f.write('#!/bin/sh\nhere=$(dirname "$(readlink -f "$0")")\nexec "$here/usr/bin/mhgu-de-installer" "$@"\n')
        os.chmod(os.path.join(app, 'AppRun'), 0o755)
        os.chmod(os.path.join(app, 'usr/bin/mhgu-de-installer'), 0o755)
        sq = os.path.join(tmp, 'app.squashfs')
        subprocess.run(['mksquashfs', app, sq, '-root-owned', '-noappend', '-comp', 'zstd', '-Xcompression-level', '19',
                        '-b', '1M', '-quiet', '-no-progress'], check=True)
        out = os.path.join(DIST, '%s-%s-%s.AppImage' % (NAME, ver, arch))
        with open(out, 'wb') as o:
            for part in (runtime, sq):
                with open(part, 'rb') as i:
                    shutil.copyfileobj(i, o)
        os.chmod(out, 0o755)
    return out


def main():
    a, archs = sys.argv[1:], list(ARCHS)
    if '--arch' in a:
        i = a.index('--arch')
        archs = a[i + 1:i + 2]
        del a[i:i + 2]
    if a not in ([], ['--exe'], ['--appimage']) or len(archs) not in (1, len(ARCHS)) or set(archs) - set(ARCHS):
        sys.exit(__doc__)
    kinds = [a[0][2:]] if a else ['exe', 'appimage']
    ver = tomllib.load(open(os.path.join(INST, 'Cargo.toml'), 'rb'))['workspace']['package']['version']
    os.makedirs(DIST, exist_ok=True)
    built = [(exe if k == 'exe' else appimage)(ver, arch) for k in kinds for arch in archs]
    sums = os.path.join(DIST, 'SHA256SUMS-%s' % ver)
    with open(sums, 'w', newline='\n') as f:
        for p in built:
            f.write('%s  %s\n' % (hashlib.sha256(open(p, 'rb').read()).hexdigest(), os.path.basename(p)))
    for p in built + [sums]:
        print('%12d %s' % (os.path.getsize(p), os.path.relpath(p, INST)))


if __name__ == '__main__':
    main()
