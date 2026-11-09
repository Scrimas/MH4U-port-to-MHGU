"""build.py : the installer's release files into installer/dist/ (MHGU_Editor's app/packaging/build.sh, in Python: the
repo has no shell scripts):
  MH4U-Port-Installer-<v>-x86_64.exe        Windows 10/11, mingw-w64 cross build, one file
  MH4U-Port-Installer-<v>-x86_64.AppImage   Linux, glibc 2.28 (cargo-zigbuild), AppImage type 2 runtime
  SHA256SUMS-<v>                            the files' sha256 (the installer's self-update checks them)

  python3 installer/packaging/build.py [--appimage | --exe]

Needs: rustup target x86_64-pc-windows-gnu + mingw-w64-gcc (exe); cargo-zigbuild + zig (else the binary needs this
machine's glibc or newer), mksquashfs (squashfs-tools) and APPIMAGE_RUNTIME=<the type 2 runtime file> (AppImage). CI:
.github/workflows/installer.yml, in an Arch Linux container like the editor's.
"""
import hashlib, os, shutil, subprocess, sys, tempfile, tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
INST = os.path.dirname(HERE)
DIST = os.path.join(INST, 'dist')
NAME = 'MH4U-Port-Installer'


def run(*a):
    print('$', ' '.join(a), flush=True)
    subprocess.run(a, cwd=INST, check=True)


def has(cmd):
    return shutil.which(cmd) is not None


def exe(ver):
    run('cargo', 'build', '--release', '--locked', '-p', 'mh4uport-installer', '--target', 'x86_64-pc-windows-gnu')
    out = os.path.join(DIST, '%s-%s-x86_64.exe' % (NAME, ver))
    shutil.copy(os.path.join(INST, 'target/x86_64-pc-windows-gnu/release/mh4uport-installer.exe'), out)
    return out


def appimage(ver):
    if has('zig') and subprocess.run(['cargo', 'zigbuild', '--help'], capture_output=True).returncode == 0:
        run('cargo', 'zigbuild', '--release', '--locked', '-p', 'mh4uport-installer', '--target', 'x86_64-unknown-linux-gnu.2.28')
        binary = os.path.join(INST, 'target/x86_64-unknown-linux-gnu/release/mh4uport-installer')
    else:
        print('   (cargo-zigbuild not found: linking against this machine\'s glibc)')
        run('cargo', 'build', '--release', '--locked', '-p', 'mh4uport-installer')
        binary = os.path.join(INST, 'target/release/mh4uport-installer')
    runtime = os.environ.get('APPIMAGE_RUNTIME')
    if not runtime or not os.path.isfile(runtime) or not has('mksquashfs'):
        sys.exit('the AppImage needs APPIMAGE_RUNTIME=<type 2 runtime> and mksquashfs')
    with tempfile.TemporaryDirectory() as tmp:
        app = os.path.join(tmp, 'AppDir')
        for d in ('usr/bin', 'usr/share/applications', 'usr/share/icons/hicolor/256x256/apps'):
            os.makedirs(os.path.join(app, d))
        shutil.copy(binary, os.path.join(app, 'usr/bin/mh4uport-installer'))
        desktop = os.path.join(HERE, 'mh4uport-installer.desktop')
        icon = os.path.join(INST, 'gui/assets/icon-256.png')
        shutil.copy(desktop, os.path.join(app, 'usr/share/applications'))
        shutil.copy(desktop, app)
        shutil.copy(icon, os.path.join(app, 'usr/share/icons/hicolor/256x256/apps/mh4uport-installer.png'))
        shutil.copy(icon, os.path.join(app, 'mh4uport-installer.png'))
        os.symlink('mh4uport-installer.png', os.path.join(app, '.DirIcon'))
        with open(os.path.join(app, 'AppRun'), 'w', newline='\n') as f:
            f.write('#!/bin/sh\nhere=$(dirname "$(readlink -f "$0")")\nexec "$here/usr/bin/mh4uport-installer" "$@"\n')
        os.chmod(os.path.join(app, 'AppRun'), 0o755)
        os.chmod(os.path.join(app, 'usr/bin/mh4uport-installer'), 0o755)
        sq = os.path.join(tmp, 'app.squashfs')
        subprocess.run(['mksquashfs', app, sq, '-root-owned', '-noappend', '-comp', 'zstd', '-Xcompression-level', '19',
                        '-b', '1M', '-quiet', '-no-progress'], check=True)
        out = os.path.join(DIST, '%s-%s-x86_64.AppImage' % (NAME, ver))
        with open(out, 'wb') as o:
            for part in (runtime, sq):
                with open(part, 'rb') as i:
                    shutil.copyfileobj(i, o)
        os.chmod(out, 0o755)
    return out


def main():
    a = sys.argv[1:]
    if a not in ([], ['--appimage'], ['--exe']):
        sys.exit(__doc__)
    ver = tomllib.load(open(os.path.join(INST, 'Cargo.toml'), 'rb'))['workspace']['package']['version']
    os.makedirs(DIST, exist_ok=True)
    built = []
    if a != ['--appimage']:
        built.append(exe(ver))
    if a != ['--exe']:
        built.append(appimage(ver))
    sums = os.path.join(DIST, 'SHA256SUMS-%s' % ver)
    with open(sums, 'w', newline='\n') as f:
        for p in built:
            f.write('%s  %s\n' % (hashlib.sha256(open(p, 'rb').read()).hexdigest(), os.path.basename(p)))
    for p in built + [sums]:
        print('%12d %s' % (os.path.getsize(p), os.path.relpath(p, INST)))


if __name__ == '__main__':
    main()
