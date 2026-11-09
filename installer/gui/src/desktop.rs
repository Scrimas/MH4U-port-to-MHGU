//! The installer puts itself in the system's menu, as MHGU_Editor does (app/gui/src/desktop.rs, from which the Linux
//! half is taken):
//! - Linux, run as an AppImage: a desktop entry pointing at the AppImage, and the icon, in the user's data folder
//!   (`~/.local/share/applications`, `~/.local/share/icons/hicolor`). `TryExec` hides the entry once that AppImage is
//!   deleted.
//! - Windows, run as a release .exe (not a cargo build): a shortcut in the user's Start Menu
//!   (`%APPDATA%\Microsoft\Windows\Start Menu\Programs`).
//!
//! The newest version keeps the entry: an older copy takes it only when the file it names is gone. A self-update
//! (selfupdate.rs) renames the file to the new version: `moved` points the entry at the new file at once, so the menu
//! keeps working even if the new version is not started before the old one is gone.

use mhgu_de_core::VERSION;
use mhgu_de_core::version::Version;
use std::path::Path;

/// The entry's name, the icon's and the window's Wayland app id / X11 class (main.rs).
#[cfg_attr(windows, allow(dead_code))]
pub const NAME: &str = "mhgu-de-installer";

/// Write or refresh the entry when started from a release file; nothing otherwise.
pub fn install() {
    #[cfg(target_os = "linux")]
    linux::install();
    #[cfg(windows)]
    win::install();
}

/// After a self-update replaced `old` with `new` (version `version`): the entry that named `old` names `new`.
#[allow(unused_variables)]
pub fn moved(old: &Path, new: &Path, version: &str) {
    #[cfg(target_os = "linux")]
    linux::moved(old, new, version);
    #[cfg(windows)]
    win::moved(old, new);
}

/// `a` is newer than `b` (an unreadable version is older than any).
#[allow(dead_code)]
fn newer(a: Option<&str>, b: &str) -> bool {
    a.and_then(Version::parse) > Version::parse(b)
}

#[cfg(target_os = "linux")]
mod linux {
    use super::{NAME, VERSION, newer};
    use std::path::Path;

    const ENTRY: &str = include_str!("../../packaging/mhgu-de-installer.desktop");
    const PNG: &[u8] = include_bytes!("../assets/icon-256.png");

    pub fn install() {
        let Some(appimage) = std::env::var_os("APPIMAGE") else { return };
        let Some(data) = dirs::data_dir() else { return };
        let Some(path) = Path::new(&appimage).to_str().filter(|p| usable(p)) else { return };
        let file = data.join("applications").join(format!("{NAME}.desktop"));
        if let Ok(old) = std::fs::read_to_string(&file) {
            let alive = field(&old, "TryExec").is_some_and(|p| Path::new(&unescape(p)).is_file());
            if alive && newer(field(&old, "X-AppImage-Version"), VERSION) {
                return;
            }
        }
        // NixOS: the menu starts the unpacked binary through a small launcher script
        let launcher = nixos_unpacked().and_then(|bin| {
            let script = data.join(NAME).join("nixos-launch.sh");
            let text = launcher_script(path, &bin.to_string_lossy(), &stamp(Path::new(path))?);
            match write(&script, text.as_bytes()).and_then(|_| executable(&script)) {
                Ok(()) => script.to_str().map(str::to_owned),
                Err(e) => {
                    eprintln!("desktop entry: {}: {e}", script.display());
                    None
                }
            }
        });
        let icon = data.join(format!("icons/hicolor/256x256/apps/{NAME}.png"));
        for (p, b) in [(file, entry(path, launcher.as_deref(), VERSION).into_bytes()), (icon, PNG.to_vec())] {
            if let Err(e) = write(&p, &b) {
                eprintln!("desktop entry: {}: {e}", p.display());
            }
        }
    }

    pub fn moved(old: &Path, new: &Path, version: &str) {
        if let Some(data) = dirs::data_dir() {
            moved_in(&data, old, new, version);
        }
    }

    /// `moved` with the data folder given (the tests').
    pub(super) fn moved_in(data: &Path, old: &Path, new: &Path, version: &str) {
        let Some(path) = new.to_str().filter(|p| usable(p)) else { return };
        let file = data.join("applications").join(format!("{NAME}.desktop"));
        let Ok(cur) = std::fs::read_to_string(&file) else { return };
        if field(&cur, "TryExec").map(unescape).as_deref() != old.to_str() {
            return;
        }
        // straight at the new AppImage: started once (the restart after the update), it points the entry at its own
        // unpacked binary again on NixOS
        if let Err(e) = write(&file, entry(path, None, version).as_bytes()) {
            eprintln!("desktop entry: {}: {e}", file.display());
        }
    }

    /// An absolute path on one line: a desktop entry can name it.
    fn usable(p: &str) -> bool {
        p.starts_with('/') && !p.contains('\n')
    }

    /// The packaged entry with `Exec` on the AppImage of `version`, or on `launcher` (NixOS); `TryExec` stays on the
    /// AppImage, so the entry goes once the AppImage is deleted.
    pub(super) fn entry(appimage: &str, launcher: Option<&str>, version: &str) -> String {
        let mut out = String::new();
        for l in ENTRY.lines() {
            if l.starts_with("Exec=") {
                out += &format!(
                    "Exec={}\nTryExec={}\n",
                    quote(launcher.unwrap_or(appimage)),
                    appimage.replace('\\', "\\\\")
                );
            } else {
                out += l;
                out += "\n";
            }
        }
        out + &format!("X-AppImage-Version={version}\n")
    }

    /// NixOS runs an AppImage through appimage-run, which unpacks it once into `~/.cache/appimage-run/<sha256>/` but
    /// then hashes it and builds a bubblewrap sandbox on every start. Where nix-ld is on, the unpacked binary runs
    /// without them: this is that binary when the installer runs that way, None anywhere else (other distributions,
    /// NixOS without nix-ld, an AppImage started by other means).
    fn nixos_unpacked() -> Option<std::path::PathBuf> {
        std::env::var_os("NIX_LD")?;
        let os = std::fs::read_to_string("/etc/os-release").ok()?;
        if !os.lines().any(|l| matches!(l.trim(), "ID=nixos" | "ID=\"nixos\"")) {
            return None;
        }
        let exe = std::env::current_exe().ok()?;
        exe.components().any(|c| c.as_os_str() == "appimage-run").then_some(exe)
    }

    /// Size and modification time of `p`, as `stat -Lc %s:%Y` prints them.
    pub(super) fn stamp(p: &Path) -> Option<String> {
        let m = std::fs::metadata(p).ok()?;
        Some(format!("{}:{}", m.len(), m.modified().ok()?.duration_since(std::time::UNIX_EPOCH).ok()?.as_secs()))
    }

    /// Starts `bin` (unpacked from `appimage`) while the AppImage is still the file it came from (`stamp`), as if
    /// appimage-run had started it; otherwise, or when the binary cannot start at all, the AppImage the usual way. The
    /// shell reports a binary that could not start as 127 (no loader: NixOS without nix-ld; a library missing) or 126
    /// (not executable, a bad interpreter).
    pub(super) fn launcher_script(appimage: &str, bin: &str, stamp: &str) -> String {
        let sq = |s: &str| format!("'{}'", s.replace('\'', "'\\''"));
        format!(
            "#!/bin/sh\n\
             # Written by MHGU Definitive Edition Installer on NixOS: skips appimage-run's sandbox on each start.\n\
             app={}\n\
             bin={}\n\
             if [ -x \"$bin\" ] && [ \"$(stat -Lc %s:%Y \"$app\" 2>/dev/null)\" = {} ]; then\n\
             \x20   APPIMAGE=\"$app\" \"$bin\" \"$@\"\n\
             \x20   status=$?\n\
             \x20   case \"$status\" in 126 | 127) ;; *) exit \"$status\" ;; esac\n\
             fi\n\
             exec \"$app\" \"$@\"\n",
            sq(appimage),
            sq(bin),
            sq(stamp)
        )
    }

    pub(super) fn executable(p: &Path) -> std::io::Result<()> {
        use std::os::unix::fs::PermissionsExt;
        std::fs::set_permissions(p, std::fs::Permissions::from_mode(0o755))
    }

    /// An `Exec` argument: double quotes with `"` `` ` `` `$` `\` escaped, then the string escape doubles every
    /// backslash, and `%` is doubled for field codes.
    pub(super) fn quote(s: &str) -> String {
        let mut q = String::from("\"");
        for c in s.chars() {
            match c {
                '"' | '`' | '$' => q += &format!("\\\\{c}"),
                '\\' => q += "\\\\\\\\",
                '%' => q += "%%",
                _ => q.push(c),
            }
        }
        q + "\""
    }

    pub(super) fn unescape(s: &str) -> String {
        s.replace("\\\\", "\\")
    }

    pub(super) fn field<'a>(entry: &'a str, key: &str) -> Option<&'a str> {
        entry.lines().find_map(|l| l.strip_prefix(key)?.strip_prefix('='))
    }

    /// Write only when different, through a temporary file so the desktop never reads half.
    fn write(p: &Path, b: &[u8]) -> std::io::Result<()> {
        if std::fs::read(p).is_ok_and(|old| old == b) {
            return Ok(());
        }
        std::fs::create_dir_all(p.parent().unwrap())?;
        let tmp = p.with_extension("tmp");
        std::fs::write(&tmp, b)?;
        std::fs::rename(&tmp, p)
    }
}

#[cfg(windows)]
mod win {
    use super::{VERSION, newer};
    use std::os::windows::ffi::{OsStrExt, OsStringExt};
    use std::path::{Path, PathBuf};
    use windows::Win32::Storage::FileSystem::{
        GetFileVersionInfoSizeW, GetFileVersionInfoW, VS_FIXEDFILEINFO, VerQueryValueW,
    };
    use windows::Win32::System::Com::{
        CLSCTX_INPROC_SERVER, COINIT_APARTMENTTHREADED, CoCreateInstance, CoInitializeEx, CoTaskMemFree,
        CoUninitialize, IPersistFile, STGM_READ,
    };
    use windows::Win32::UI::Shell::{
        FOLDERID_Programs, IShellLinkW, KF_FLAG_DEFAULT, SHGetKnownFolderPath, SLGP_RAWPATH, ShellLink,
    };
    use windows::core::{Interface, PCWSTR, w};

    /// The shortcut's name in the Start Menu.
    const LINK: &str = "MHGU Definitive Edition Installer.lnk";
    /// Its tooltip: the packaged desktop entry's Comment.
    const COMMENT: &str = "Install the MHGU Definitive Edition mod for Monster Hunter Generations Ultimate";
    /// The file cargo builds; the release's is renamed by packaging/build.py.
    const CARGO_EXE: &str = "mhgu-de-installer.exe";

    pub fn install() {
        let Ok(exe) = std::env::current_exe() else { return };
        if exe.file_name().is_none_or(|n| n.eq_ignore_ascii_case(CARGO_EXE)) {
            return;
        }
        com(|| {
            let lnk = link_file()?;
            if let Some(cur) = target(&lnk) {
                if same(&cur, &exe) {
                    return Some(());
                }
                if cur.is_file() && newer(file_version(&cur).as_deref(), VERSION) {
                    return Some(());
                }
            }
            save(&lnk, &exe).map_err(|e| eprintln!("start menu: {}: {e}", lnk.display())).ok()
        });
    }

    pub fn moved(old: &Path, new: &Path) {
        com(|| moved_in(&link_file()?, old, new));
    }

    /// `moved` with the shortcut given (the tests'); COM set up by the caller.
    pub(super) fn moved_in(lnk: &Path, old: &Path, new: &Path) -> Option<()> {
        if !same(&target(lnk)?, old) {
            return None;
        }
        save(lnk, new).map_err(|e| eprintln!("start menu: {}: {e}", lnk.display())).ok()
    }

    /// Run `f` on a thread of its own with COM set up there: the window's thread keeps its own COM state, and the
    /// caller waits (an update quits right after `moved`).
    fn com<R: Send>(f: impl FnOnce() -> Option<R> + Send) -> Option<R> {
        std::thread::scope(|s| {
            s.spawn(|| {
                let init = unsafe { CoInitializeEx(None, COINIT_APARTMENTTHREADED) };
                let r = if init.is_ok() { f() } else { None };
                if init.is_ok() {
                    unsafe { CoUninitialize() };
                }
                r
            })
            .join()
            .ok()
            .flatten()
        })
    }

    fn link_file() -> Option<PathBuf> {
        let p = unsafe { SHGetKnownFolderPath(&FOLDERID_Programs, KF_FLAG_DEFAULT, None) }.ok()?;
        let dir = PathBuf::from(unsafe { p.to_string() }.ok()?);
        unsafe { CoTaskMemFree(Some(p.0 as *const _)) };
        Some(dir.join(LINK))
    }

    fn wide(s: impl AsRef<std::ffi::OsStr>) -> Vec<u16> {
        s.as_ref().encode_wide().chain([0]).collect()
    }

    fn from_wide(b: &[u16]) -> PathBuf {
        let n = b.iter().position(|&c| c == 0).unwrap_or(b.len());
        std::ffi::OsString::from_wide(&b[..n]).into()
    }

    fn same(a: &Path, b: &Path) -> bool {
        a.as_os_str().eq_ignore_ascii_case(b.as_os_str())
    }

    /// The file shortcut `lnk` starts.
    pub(super) fn target(lnk: &Path) -> Option<PathBuf> {
        if !lnk.is_file() {
            return None;
        }
        unsafe {
            let link: IShellLinkW = CoCreateInstance(&ShellLink, None, CLSCTX_INPROC_SERVER).ok()?;
            link.cast::<IPersistFile>().ok()?.Load(PCWSTR(wide(lnk).as_ptr()), STGM_READ).ok()?;
            let mut buf = vec![0u16; 32768];
            // the path as written, environment variables not expanded
            link.GetPath(&mut buf, std::ptr::null_mut(), SLGP_RAWPATH.0 as u32).ok()?;
            Some(from_wide(&buf)).filter(|p| !p.as_os_str().is_empty())
        }
    }

    /// Write shortcut `lnk` to start `exe`, the .exe's own icon.
    pub(super) fn save(lnk: &Path, exe: &Path) -> windows::core::Result<()> {
        if let Some(dir) = lnk.parent() {
            let _ = std::fs::create_dir_all(dir);
        }
        unsafe {
            let link: IShellLinkW = CoCreateInstance(&ShellLink, None, CLSCTX_INPROC_SERVER)?;
            link.SetPath(PCWSTR(wide(exe).as_ptr()))?;
            if let Some(dir) = exe.parent() {
                link.SetWorkingDirectory(PCWSTR(wide(dir).as_ptr()))?;
            }
            link.SetIconLocation(PCWSTR(wide(exe).as_ptr()), 0)?;
            link.SetDescription(PCWSTR(wide(COMMENT).as_ptr()))?;
            link.cast::<IPersistFile>()?.Save(PCWSTR(wide(lnk).as_ptr()), true)
        }
    }

    /// The product version in `exe`'s version resource (gui/build.rs, winresource: the package's version), as
    /// major.minor.patch.
    pub(super) fn file_version(exe: &Path) -> Option<String> {
        let name = wide(exe);
        unsafe {
            let n = GetFileVersionInfoSizeW(PCWSTR(name.as_ptr()), None);
            if n == 0 {
                return None;
            }
            let mut block = vec![0u8; n as usize];
            GetFileVersionInfoW(PCWSTR(name.as_ptr()), None, n, block.as_mut_ptr().cast()).ok()?;
            let (mut p, mut len) = (std::ptr::null_mut(), 0u32);
            if !VerQueryValueW(block.as_ptr().cast(), w!("\\"), &mut p, &mut len).as_bool()
                || (len as usize) < size_of::<VS_FIXEDFILEINFO>()
            {
                return None;
            }
            let info = &*(p as *const VS_FIXEDFILEINFO);
            let (ms, ls) = (info.dwProductVersionMS, info.dwProductVersionLS);
            Some(format!("{}.{}.{}", ms >> 16, ms & 0xffff, ls >> 16))
        }
    }

    #[cfg(test)]
    pub(super) fn with_com<R: Send>(f: impl FnOnce() -> Option<R> + Send) -> Option<R> {
        com(f)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn only_a_newer_version_keeps_the_entry() {
        assert!(newer(Some("9.0.0"), VERSION));
        assert!(!newer(Some(VERSION), VERSION));
        assert!(!newer(Some("0.0.1"), VERSION));
        assert!(!newer(None, VERSION) && !newer(Some("junk"), VERSION));
    }

    #[cfg(target_os = "linux")]
    mod linux {
        use super::super::linux::*;
        use super::super::*;

        #[test]
        fn exec_points_at_the_appimage() {
            let e = entry("/home/a b/MHGU 100%.AppImage", None, VERSION);
            assert!(e.contains("Exec=\"/home/a b/MHGU 100%%.AppImage\"\n"));
            assert_eq!(field(&e, "TryExec"), Some("/home/a b/MHGU 100%.AppImage"));
            assert_eq!(field(&e, "X-AppImage-Version"), Some(VERSION));
            assert_eq!(field(&e, "StartupWMClass"), Some(NAME), "the window's app id (main.rs)");
            assert_eq!(e.matches("Exec=").count(), 2);
        }

        #[test]
        fn nixos_entry_runs_the_launcher() {
            let e =
                entry("/home/a/MHGU.AppImage", Some("/home/a/.local/share/mhgu-de-installer/nixos-launch.sh"), VERSION);
            assert!(e.contains("Exec=\"/home/a/.local/share/mhgu-de-installer/nixos-launch.sh\"\n"));
            assert_eq!(field(&e, "TryExec"), Some("/home/a/MHGU.AppImage"));
        }

        #[test]
        fn launcher_script_runs_in_sh() {
            let dir = std::env::temp_dir().join(format!("mhgu-de-launch-{}", std::process::id()));
            std::fs::create_dir_all(&dir).unwrap();
            let (app, bin) = (dir.join("it's.AppImage"), dir.join("bin"));
            std::fs::write(&app, "#!/bin/sh\necho app \"$@\"\n").unwrap();
            std::fs::write(&bin, "#!/bin/sh\necho bin \"$APPIMAGE\" \"$@\"\n").unwrap();
            executable(&app).unwrap();
            executable(&bin).unwrap();
            let script = dir.join("launch.sh");
            let run = |stamp: &str| {
                std::fs::write(&script, launcher_script(app.to_str().unwrap(), bin.to_str().unwrap(), stamp)).unwrap();
                let out = std::process::Command::new("sh").arg(&script).arg("a b").output().unwrap();
                String::from_utf8(out.stdout).unwrap()
            };
            let fresh = run(&stamp(&app).unwrap());
            let stale = run("1:2");
            // the binary cannot start: no loader or library (127), a bad interpreter (126)
            std::fs::write(&bin, "#!/bin/sh\nexit 127\n").unwrap();
            let no_lib = run(&stamp(&app).unwrap());
            std::fs::write(&bin, "#!/nonexistent/ld.so\n").unwrap();
            let no_loader = run(&stamp(&app).unwrap());
            // the app's own exit status goes back to the desktop as it is
            std::fs::write(&bin, "#!/bin/sh\nexit 3\n").unwrap();
            std::fs::write(
                &script,
                launcher_script(app.to_str().unwrap(), bin.to_str().unwrap(), &stamp(&app).unwrap()),
            )
            .unwrap();
            let code = std::process::Command::new("sh").arg(&script).status().unwrap().code();
            let _ = std::fs::remove_dir_all(&dir);
            assert_eq!(fresh, format!("bin {} a b\n", app.display()));
            assert_eq!(stale, "app a b\n");
            assert_eq!(no_lib, "app a b\n");
            assert_eq!(no_loader, "app a b\n");
            assert_eq!(code, Some(3));
        }

        #[test]
        fn reserved_characters_are_escaped() {
            assert_eq!(quote(r#"/a"$`\b"#), r#""/a\\"\\$\\`\\\\b""#);
            let e = entry(r"/a\b", None, "9.9.9");
            assert_eq!(unescape(&e.lines().find(|l| l.starts_with("TryExec=")).unwrap()[8..]), r"/a\b");
        }

        #[test]
        fn an_update_moves_only_the_entry_naming_the_old_file() {
            let d = std::env::temp_dir().join(format!("mhgu-de-moved-{}", std::process::id()));
            let file = d.join(format!("applications/{NAME}.desktop"));
            std::fs::create_dir_all(file.parent().unwrap()).unwrap();
            let (old, new) =
                (Path::new("/a/Installer-2.0.0-x86_64.AppImage"), Path::new("/a/Installer-2.1.0-x86_64.AppImage"));
            std::fs::write(&file, entry("/other/Installer.AppImage", None, VERSION)).unwrap();
            moved_in(&d, old, new, "2.1.0");
            let other = std::fs::read_to_string(&file).unwrap();
            std::fs::write(&file, entry(old.to_str().unwrap(), Some("/x/nixos-launch.sh"), VERSION)).unwrap();
            moved_in(&d, old, new, "2.1.0");
            let after = std::fs::read_to_string(&file).unwrap();
            let _ = std::fs::remove_dir_all(&d);
            assert_eq!(field(&other, "TryExec"), Some("/other/Installer.AppImage"), "another copy's entry stays");
            assert_eq!(after, entry(new.to_str().unwrap(), None, "2.1.0"), "straight at the new AppImage");
        }
    }

    /// CI's Windows job runs this: a shortcut written, then read back.
    #[cfg(windows)]
    #[test]
    fn a_shortcut_names_its_exe() {
        let dir = std::env::temp_dir().join(format!("mhgu-de-lnk-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let lnk = dir.join("Test Installer.lnk");
        let exe = |v: &str| dir.join(format!("MHGU-Definitive-Edition-Installer-{v}-x86_64.exe"));
        std::fs::write(exe("9.9.9"), "x").unwrap();
        let read = win::with_com(|| {
            win::save(&lnk, &exe("9.9.9")).unwrap();
            let written = win::target(&lnk);
            // a self-update: only the shortcut naming the old file follows it
            win::moved_in(&lnk, &exe("1.0.0"), &exe("10.0.0"));
            let other = win::target(&lnk);
            win::moved_in(&lnk, &exe("9.9.9"), &exe("10.0.0"));
            Some((written, other, win::target(&lnk)))
        });
        let _ = std::fs::remove_dir_all(&dir);
        let (written, other, after) = read.unwrap();
        assert_eq!(written, Some(exe("9.9.9")));
        assert_eq!(other, Some(exe("9.9.9")), "another copy's shortcut stays");
        assert_eq!(after, Some(exe("10.0.0")));
        // the version an older copy compares with: this binary's resource (gui/build.rs, winresource)
        let v = win::file_version(&std::env::current_exe().unwrap());
        assert_eq!(v.as_deref(), VERSION.split('-').next());
    }
}
