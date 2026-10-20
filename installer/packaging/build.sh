#!/usr/bin/env bash
# Build the installer apps into installer/dist/ (code only: no game data is read, so hosted CI can run it):
#   MH4U-Port-Installer-<version>-x86_64.AppImage   Linux, single file
#   MH4U-Port-Installer-<version>-x86_64.exe        Windows 10/11, single file
# Same toolchain as MHGU_Editor's app/packaging/build.sh: rustup with x86_64-pc-windows-gnu, mingw-w64-gcc,
# squashfs-tools; cargo-zigbuild + zig for a glibc 2.28 Linux binary; APPIMAGE_RUNTIME=path to the AppImage type 2
# runtime (github.com/AppImage/type2-runtime) or appimagetool in PATH. MH4UPORT_REPO=OWNER/NAME = the repository
# whose latest release the apps install (default in src/core.rs).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
app=$(dirname "$here")
cd "$app"
ver=$(sed -n 's/^version = "\(.*\)"/\1/p' Cargo.toml | head -1)
dist="$app/dist"
mkdir -p "$dist"
name="MH4U-Port-Installer-$ver-x86_64"

echo "== Windows"
cargo build --release --target x86_64-pc-windows-gnu
cp target/x86_64-pc-windows-gnu/release/mh4uport-installer.exe "$dist/$name.exe"

echo "== Linux"
if cargo zigbuild --help >/dev/null 2>&1 && command -v zig >/dev/null; then
    cargo zigbuild --release --target x86_64-unknown-linux-gnu.2.28
    bin=target/x86_64-unknown-linux-gnu/release/mh4uport-installer
else
    echo "   (cargo-zigbuild not found: linking against this machine's glibc)"
    cargo build --release
    bin=target/release/mh4uport-installer
fi
echo "   needs glibc $(objdump -T "$bin" | grep -o 'GLIBC_[0-9.]*' | sort -Vu | tail -1)"

appdir=$(mktemp -d)/AppDir
mkdir -p "$appdir/usr/bin" "$appdir/usr/share/applications" "$appdir/usr/share/icons/hicolor/256x256/apps"
install -m755 "$bin" "$appdir/usr/bin/mh4uport-installer"
install -m644 packaging/mh4uport-installer.desktop "$appdir/usr/share/applications/"
install -m644 packaging/mh4uport-installer.desktop "$appdir/"
install -m644 packaging/icon-256.png "$appdir/usr/share/icons/hicolor/256x256/apps/mh4uport-installer.png"
install -m644 packaging/icon-256.png "$appdir/mh4uport-installer.png"
ln -s mh4uport-installer.png "$appdir/.DirIcon"
cat > "$appdir/AppRun" <<'EOF'
#!/bin/sh
here=$(dirname "$(readlink -f "$0")")
exec "$here/usr/bin/mh4uport-installer" "$@"
EOF
chmod 755 "$appdir/AppRun"

out="$dist/$name.AppImage"
if command -v appimagetool >/dev/null; then
    ARCH=x86_64 appimagetool --no-appstream "$appdir" "$out"
elif [ -n "${APPIMAGE_RUNTIME:-}" ]; then
    sq=$(mktemp)
    mksquashfs "$appdir" "$sq" -root-owned -noappend -comp zstd -quiet -no-progress
    cat "$APPIMAGE_RUNTIME" "$sq" > "$out"
    chmod 755 "$out"
    rm -f "$sq"
else
    echo "no appimagetool and no APPIMAGE_RUNTIME: AppDir left at $appdir" >&2
    exit 1
fi
rm -rf "$(dirname "$appdir")"
(cd "$dist" && sha256sum "$name".* > "SHA256SUMS-installer-$ver")
ls -la "$dist"
