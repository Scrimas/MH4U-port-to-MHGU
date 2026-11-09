//! The installer's own update (the save editor's way, MHGU_Editor app/gui/src/update.rs): the newest installer release
//! of the mod's repository (source.rs installer_releases; never the mod's) is compared with this version; when the
//! player asks, its AppImage or .exe is downloaded beside the running file, checked against the release's
//! `SHA256SUMS-<version>` and swapped in, renamed to the new version when the old name held the old one. Windows
//! cannot delete a running .exe: it is renamed aside and deleted at the next start (settings update_leftover).
//! The checksums catch a broken download, not a release published by someone else (there is no signature).

use crate::i18n::{tr, trf};
use crate::source::{Asset, INSTALLER_ASSET, Release, Source};
use crate::version::Version;
use std::path::{Path, PathBuf};
use std::sync::atomic::AtomicBool;

#[cfg(windows)]
pub const SUFFIX: &str = "-x86_64.exe";
#[cfg(not(windows))]
pub const SUFFIX: &str = "-x86_64.AppImage";

/// An installer release newer than this one, with this platform's file and its checksums.
#[derive(Clone, Debug)]
pub struct Update {
    pub release: Release,
    pub version: Version,
    file: Asset,
    sums: Asset,
}

impl Update {
    pub fn size(&self) -> u64 {
        self.file.size
    }
}

/// The newest installer release when it is newer than `current`.
pub fn available(all: &[Release], current: &str) -> Option<Update> {
    let cur = Version::parse(current);
    crate::source::installer_releases(all).into_iter().find_map(|r| {
        let v = r.version()?;
        let file = r.assets.iter().find(|a| a.name.starts_with(INSTALLER_ASSET) && a.name.ends_with(SUFFIX))?.clone();
        let sums = r.asset(&format!("SHA256SUMS-{v}"))?.clone();
        (Some(v) > cur).then(|| Update { release: r.clone(), version: v, file, sums })
    })
}

/// The file an update replaces: the .exe, or the AppImage ($APPIMAGE); None when run another way (cargo run).
pub fn target() -> Option<PathBuf> {
    #[cfg(windows)]
    return std::env::current_exe().ok();
    #[cfg(not(windows))]
    std::env::var_os("APPIMAGE").map(PathBuf::from)
}

/// The updated file's name: the version in `name` becomes `to`; a name without it stays.
fn renamed(name: &str, from: &str, to: &str) -> String {
    name.replacen(&format!("-{from}-"), &format!("-{to}-"), 1)
}

/// The hash of `name` in a `sha256sum` listing.
fn sum_of(list: &str, name: &str) -> Option<String> {
    list.lines().find_map(|l| {
        let (h, n) = l.split_once(char::is_whitespace)?;
        (n.trim_start().trim_start_matches('*') == name).then(|| h.to_ascii_lowercase())
    })
}

/// What `install` did: the new file, and on Windows the old .exe set aside (to delete at the next start).
pub struct Installed {
    pub file: PathBuf,
    pub aside: Option<PathBuf>,
}

/// Download, check and swap in update `u` for `old` (the `target`).
pub fn install(
    src: &Source,
    u: &Update,
    old: &Path,
    progress: &dyn Fn(u64, u64),
    cancel: &AtomicBool,
) -> Result<Installed, String> {
    let list = String::from_utf8_lossy(&src.bytes(&u.sums)?).into_owned();
    let want = sum_of(&list, &u.file.name).ok_or_else(|| trf("{} is not in {}", &[&u.file.name, &u.sums.name]))?;
    let name = old.file_name().and_then(|n| n.to_str()).ok_or_else(|| tr("The running file has no usable name"))?;
    let new = old.with_file_name(renamed(name, crate::VERSION, &u.version.to_string()));
    let part = new.with_file_name(format!("{}.download", new.file_name().unwrap().to_string_lossy()));
    let res = src.download(&u.file, &part, progress, cancel).and_then(|got| {
        if got != want {
            return Err(tr("The download does not match the release's checksum"));
        }
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            std::fs::set_permissions(&part, std::fs::Permissions::from_mode(0o755))
                .map_err(|e| trf("Could not write {} ({})", &[&part.display(), &e]))?;
        }
        swap(old, &part, &new)
    });
    if res.is_err() {
        let _ = std::fs::remove_file(&part);
    }
    res.map(|aside| Installed { file: new, aside })
}

/// The new file takes the old one's place. A running AppImage can be deleted (it stays mounted until it exits); a
/// running .exe only renamed: returned, to delete later.
fn swap(old: &Path, part: &Path, new: &Path) -> Result<Option<PathBuf>, String> {
    let err = |e: std::io::Error| trf("Could not replace {} ({})", &[&old.display(), &e]);
    if cfg!(windows) {
        let aside = old.with_file_name(format!("{}.old", old.file_name().unwrap().to_string_lossy()));
        let _ = std::fs::remove_file(&aside);
        std::fs::rename(old, &aside).map_err(err)?;
        if let Err(e) = std::fs::rename(part, new) {
            let _ = std::fs::rename(&aside, old);
            return Err(err(e));
        }
        Ok(Some(aside))
    } else {
        std::fs::rename(part, new).map_err(err)?;
        if new != old {
            let _ = std::fs::remove_file(old);
        }
        Ok(None)
    }
}

/// At start: delete the .exe an update left aside; true when it is gone.
pub fn cleanup(leftover: &Path) -> bool {
    std::fs::remove_file(leftover).is_ok() || !leftover.exists()
}

/// Start the updated file.
pub fn restart(exe: &Path) -> std::io::Result<()> {
    let mut c = std::process::Command::new(exe);
    // the AppImage runtime's variables describe this AppImage, not the new one
    for v in ["APPIMAGE", "APPDIR", "ARGV0", "OWD"] {
        c.env_remove(v);
    }
    c.spawn().map(drop)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rel(tag: &str, assets: &[&str]) -> Release {
        Release {
            tag: tag.into(),
            page: String::new(),
            date: String::new(),
            draft: false,
            prerelease: false,
            assets: assets.iter().map(|n| Asset { name: n.to_string(), url: n.to_string(), size: 3 }).collect(),
        }
    }

    #[test]
    fn only_a_newer_installer_with_its_file_and_sums_is_offered() {
        let f = |v: &str| format!("MHGU-Definitive-Edition-Installer-{v}{SUFFIX}");
        let all = [
            rel("v9.0.0", &["core-9.0.0.zip", "SHA256SUMS-9.0.0"]),
            rel("v2.2.0", &[&f("2.2.0")]),
            rel("v2.1.0", &[&f("2.1.0"), "SHA256SUMS-2.1.0"]),
        ];
        let u = available(&all, "2.0.0").unwrap();
        assert_eq!(u.version.to_string(), "2.1.0", "2.2.0 has no checksums, the mod's v9 is not an installer");
        assert!(available(&all, "2.1.0").is_none());
    }

    #[test]
    fn names_and_checksums() {
        assert_eq!(
            renamed("MHGU-Definitive-Edition-Installer-1.0.0-x86_64.AppImage", "1.0.0", "1.1.0"),
            "MHGU-Definitive-Edition-Installer-1.1.0-x86_64.AppImage"
        );
        assert_eq!(renamed("installer.exe", "1.0.0", "1.1.0"), "installer.exe");
        let list = "AAA  MHGU-Definitive-Edition-Installer-1.1.0-x86_64.AppImage\nbbb *MHGU-Definitive-Edition-Installer-1.1.0-x86_64.exe\n";
        assert_eq!(sum_of(list, "MHGU-Definitive-Edition-Installer-1.1.0-x86_64.AppImage").as_deref(), Some("aaa"));
        assert_eq!(sum_of(list, "MHGU-Definitive-Edition-Installer-1.1.0-x86_64.exe").as_deref(), Some("bbb"));
        assert_eq!(sum_of(list, "other"), None);
    }

    #[test]
    fn swap_replaces_the_old_file() {
        let d = std::env::temp_dir().join(format!("mhgu-de-update-{}", std::process::id()));
        std::fs::create_dir_all(&d).unwrap();
        let (old, part, new) = (d.join("a-1-x"), d.join("a-2-x.download"), d.join("a-2-x"));
        std::fs::write(&old, "old").unwrap();
        std::fs::write(&part, "new").unwrap();
        let aside = swap(&old, &part, &new).unwrap();
        assert_eq!(aside.is_some(), cfg!(windows));
        assert_eq!(std::fs::read_to_string(&new).unwrap(), "new");
        assert!(!part.exists() && (!old.exists() || cfg!(windows)));
        std::fs::remove_dir_all(&d).unwrap();
    }

    #[test]
    fn a_local_update_installs_and_a_bad_checksum_is_refused() {
        let d = std::env::temp_dir().join(format!("mhgu-de-update-src-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(d.join("rel")).unwrap();
        let name = format!("MHGU-Definitive-Edition-Installer-9.9.9{SUFFIX}");
        std::fs::write(d.join("rel").join(&name), "new build").unwrap();
        let sum = crate::source::sha256_file(&d.join("rel").join(&name)).unwrap();
        std::fs::write(d.join("rel/SHA256SUMS-9.9.9"), format!("{sum}  {name}\n")).unwrap();
        let mk = |n: &str, size: u64| Asset { name: n.into(), url: n.into(), size };
        let r = Release { assets: vec![mk(&name, 9), mk("SHA256SUMS-9.9.9", 100)], ..rel("v9.9.9", &[]) };
        let u = available(&[r], crate::VERSION).unwrap();
        let old = d.join(format!("MHGU-Definitive-Edition-Installer-{}{SUFFIX}", crate::VERSION));
        std::fs::write(&old, "old build").unwrap();
        let src = Source::Local(d.join("rel"));
        let done = install(&src, &u, &old, &|_, _| {}, &AtomicBool::new(false)).unwrap();
        assert_eq!(done.file, d.join(&name));
        assert_eq!(std::fs::read_to_string(&done.file).unwrap(), "new build");
        std::fs::write(d.join("rel/SHA256SUMS-9.9.9"), format!("{}  {name}\n", "0".repeat(64))).unwrap();
        let old2 = d.join("other.exe");
        std::fs::write(&old2, "x").unwrap();
        assert!(install(&src, &u, &old2, &|_, _| {}, &AtomicBool::new(false)).is_err());
        assert_eq!(std::fs::read_to_string(&old2).unwrap(), "x", "the running file is untouched");
        std::fs::remove_dir_all(&d).unwrap();
    }
}
