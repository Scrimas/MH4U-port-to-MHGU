//! Install places: Ryujinx, the yuzu family (yuzu, suyu, sudachi, citron, eden, torzu), MHGU PC Recomp (untested),
//! Atmosphère SD cards and any folder. Each knows where the mod goes and where its install record is kept.
//!
//! - Ryujinx: `<data>/mods/contents/0100770008dd8000/MHGU Definitive Edition`, data = `<config>/Ryujinx` (Linux
//!   ~/.config, Windows %APPDATA%), its Flatpaks, or a folder picked by the player (portable Ryujinx).
//! - yuzu family: `<load>/0100770008DD8000/MHGU Definitive Edition`, load = `<data>/load` (Linux ~/.local/share/<name>,
//!   Windows %APPDATA%\<name>, Flatpaks `~/.var/app/*/data/<name>`) unless qt-config.ini names another load folder.
//! - MHGU PC Recomp: `<folder of mhgurecomp>/mods/MHGU Definitive Edition` (or $MHGU_MODS_DIR); a new mod folder loads,
//!   enabled, unless mods/load_order.txt marks it `# off:` (morerokk/MHGURecomp runtime/mods.c, via DeepWiki: strong,
//!   not confirmed; the port never ran there).
//! - Atmosphère SD card: `atmosphere/contents/0100770008DD8000/{exefs,romfs}`, the IPS in
//!   `atmosphere/exefs_patches/MHGU Definitive Edition/` (other mods share contents/<title>: only our files are
//!   touched).
//! - Folder: `<folder>/MHGU Definitive Edition`.
//!
//! Before 2.0.0 the mod was called MH4U Port: a v1.x release extracted by hand left a `MH4U Port` folder (SD card:
//! `romfs/nativeNX/mh4uport`, `exefs_patches/MH4U Port`). It counts as a hand install and goes with the next install
//! or removal (Place::legacy), or the emulator would load the module twice.

use crate::i18n::{tr, trf};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

pub const TITLE_ID: &str = "0100770008DD8000";
/// The mod's data folder (module/port.c DATA_DIR), below the mod folder.
pub const DATA_DIR: &str = "romfs/nativeNX/mhgu_de";
/// The mod folder of the releases before 2.0.0, and their data folder.
pub const LEGACY_FOLDER: &str = "MH4U Port";
pub const LEGACY_DATA_DIR: &str = "romfs/nativeNX/mh4uport";

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Kind {
    Ryujinx,
    Yuzu,
    Recomp,
    SdCard,
    Folder,
}

impl Kind {
    pub fn key(self) -> &'static str {
        match self {
            Kind::Ryujinx => "ryujinx",
            Kind::Yuzu => "yuzu",
            Kind::Recomp => "recomp",
            Kind::SdCard => "sdcard",
            Kind::Folder => "folder",
        }
    }

    pub fn from_key(k: &str) -> Option<Kind> {
        [Kind::Ryujinx, Kind::Yuzu, Kind::Recomp, Kind::SdCard, Kind::Folder].into_iter().find(|x| x.key() == k)
    }
}

/// A place the player added by hand (Settings, or the folder picker): kept in the settings.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Custom {
    pub kind: Kind,
    pub path: PathBuf,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Place {
    pub kind: Kind,
    /// Shown: "Ryujinx", "Eden (Flatpak)", "SD card E:\"…
    pub name: String,
    /// Ryujinx / yuzu: the emulator's data folder; recomp: the folder of mhgurecomp; SD card: the card's root;
    /// folder: the folder that receives `MHGU Definitive Edition`.
    pub root: PathBuf,
    /// Added by the player (kept in the settings), not found by itself.
    pub custom: bool,
}

/// Where a place's files go.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Layout {
    /// Everything in one folder `<dir>/{exefs,romfs}`, swapped whole on install.
    ModFolder(PathBuf),
    /// Atmosphère: file by file in the card's shared folders.
    Atmosphere(PathBuf),
}

impl Place {
    pub fn id(&self) -> String {
        format!("{}:{}", self.kind.key(), self.root.display())
    }

    pub fn found(&self) -> bool {
        self.root.is_dir()
    }

    pub fn untested(&self) -> bool {
        self.kind == Kind::Recomp
    }

    pub fn layout(&self, mod_folder: &str) -> Layout {
        match self.kind {
            Kind::SdCard => Layout::Atmosphere(self.root.clone()),
            Kind::Ryujinx => {
                Layout::ModFolder(self.root.join("mods/contents").join(TITLE_ID.to_lowercase()).join(mod_folder))
            }
            Kind::Yuzu => Layout::ModFolder(yuzu_load_dir(&self.root).join(TITLE_ID).join(mod_folder)),
            Kind::Recomp => Layout::ModFolder(recomp_mods_dir(&self.root).join(mod_folder)),
            Kind::Folder => Layout::ModFolder(self.root.join(mod_folder)),
        }
    }

    /// The install record (record.rs): in the mod folder, on an SD card in `contents/<title>`.
    pub fn record_path(&self, mod_folder: &str) -> PathBuf {
        match self.layout(mod_folder) {
            Layout::ModFolder(d) => d.join(crate::record::FILE),
            Layout::Atmosphere(r) => r.join("atmosphere/contents").join(TITLE_ID).join(crate::record::FILE),
        }
    }

    /// Where a manifest file (`exefs/...`, `romfs/...`) lands.
    pub fn target(&self, mod_folder: &str, rel: &str) -> PathBuf {
        match self.layout(mod_folder) {
            Layout::ModFolder(d) => d.join(rel),
            Layout::Atmosphere(r) => atmosphere_target(&r, mod_folder, rel),
        }
    }

    /// What a release before 2.0.0 left here (LEGACY_FOLDER): its mod folder; on an SD card its data folder and IPS
    /// folder (its exefs files have the same names as ours and are replaced). Empty when `mod_folder` is that name.
    pub fn legacy(&self, mod_folder: &str) -> Vec<PathBuf> {
        if mod_folder == LEGACY_FOLDER {
            return vec![];
        }
        let found = match self.layout(LEGACY_FOLDER) {
            Layout::ModFolder(d) => vec![d],
            Layout::Atmosphere(r) => vec![
                r.join("atmosphere/contents").join(TITLE_ID).join(LEGACY_DATA_DIR),
                r.join("atmosphere/exefs_patches").join(LEGACY_FOLDER),
            ],
        };
        found.into_iter().filter(|p| p.exists()).collect()
    }
}

/// SD card: `exefs/<id>.ips` -> `atmosphere/exefs_patches/<mod>/<id>.ips`, other exefs files ->
/// `atmosphere/contents/<title>/exefs/`, `romfs/...` -> `atmosphere/contents/<title>/romfs/...`.
pub fn atmosphere_target(root: &Path, mod_folder: &str, rel: &str) -> PathBuf {
    let a = root.join("atmosphere");
    match rel.strip_prefix("exefs/") {
        Some(f) if f.to_ascii_lowercase().ends_with(".ips") => a.join("exefs_patches").join(mod_folder).join(f),
        _ => a.join("contents").join(TITLE_ID).join(rel),
    }
}

/// The yuzu family's load folder: qt-config.ini's `load_directory` when it is not the default, else `<data>/load`.
pub fn yuzu_load_dir(root: &Path) -> PathBuf {
    let name = root.file_name().map(|n| n.to_os_string()).unwrap_or_default();
    let mut ini = vec![root.join("config/qt-config.ini")];
    if let Some(base) = root.parent().and_then(|d| d.parent())
        && root.parent().and_then(|d| d.file_name()).is_some_and(|d| d == "data")
    {
        ini.push(base.join("config").join(&name).join("qt-config.ini")); // a Flatpak's ~/.var/app/<id>/config
    }
    if let Some(c) = dirs::config_dir() {
        ini.push(c.join(&name).join("qt-config.ini"));
    }
    for p in ini {
        let Ok(t) = std::fs::read_to_string(&p) else { continue };
        let value = |k: &str| t.lines().find_map(|l| l.trim().strip_prefix(k).map(|v| v.trim().to_string()));
        if value("load_directory\\default=").as_deref() == Some("false")
            && let Some(v) = value("load_directory=").filter(|v| !v.is_empty())
        {
            return PathBuf::from(v);
        }
        break;
    }
    root.join("load")
}

/// MHGU PC Recomp's mods folder: $MHGU_MODS_DIR when set, else `<folder>/mods`.
pub fn recomp_mods_dir(root: &Path) -> PathBuf {
    std::env::var_os("MHGU_MODS_DIR").filter(|v| !v.is_empty()).map(PathBuf::from).unwrap_or_else(|| root.join("mods"))
}

/// A folder holding the recomp's executable.
pub fn is_recomp_folder(p: &Path) -> bool {
    p.join("mhgurecomp.exe").is_file() || p.join("mhgurecomp").is_file()
}

/// The yuzu family: data folder name, name shown.
pub const YUZU_FORKS: [(&str, &str); 6] = [
    ("yuzu", "yuzu"),
    ("suyu", "suyu"),
    ("sudachi", "Sudachi"),
    ("citron", "Citron"),
    ("eden", "Eden"),
    ("torzu", "torzu"),
];

fn sorted_dirs(p: &Path) -> Vec<PathBuf> {
    let Ok(rd) = std::fs::read_dir(p) else { return vec![] };
    let mut v: Vec<PathBuf> = rd.flatten().map(|e| e.path()).filter(|p| p.is_dir()).collect();
    v.sort();
    v
}

/// Mounted removable drives: Windows D:..Z:, Linux /run/media/$USER/*, /media/$USER/*, /media/*, /mnt/*.
fn drive_roots() -> Vec<PathBuf> {
    let mut v = vec![];
    if cfg!(windows) {
        v.extend((b'D'..=b'Z').map(|d| PathBuf::from(format!("{}:\\", d as char))).filter(|p| p.is_dir()));
    } else {
        let user = std::env::var("USER").unwrap_or_default();
        for m in [format!("/run/media/{user}"), format!("/media/{user}"), "/media".into(), "/mnt".into()] {
            v.extend(sorted_dirs(Path::new(&m)));
        }
    }
    v
}

/// The places found on this computer, then the custom ones (`custom`, from the settings; kept even when missing so
/// the player can see and remove them).
pub fn detect(custom: &[Custom]) -> Vec<Place> {
    fn push(out: &mut Vec<Place>, p: Place) {
        if !out.iter().any(|o| o.kind == p.kind && o.root == p.root) {
            out.push(p);
        }
    }
    let mut out: Vec<Place> = vec![];
    if let Some(c) = dirs::config_dir() {
        push(&mut out, Place { kind: Kind::Ryujinx, name: "Ryujinx".into(), root: c.join("Ryujinx"), custom: false });
    }
    let home = dirs::home_dir();
    if let Some(h) = &home {
        for id in ["io.github.ryubing.Ryujinx", "org.ryujinx.Ryujinx"] {
            let root = h.join(".var/app").join(id).join("config/Ryujinx");
            push(
                &mut out,
                Place { kind: Kind::Ryujinx, name: trf("{} (Flatpak)", &[&"Ryujinx"]), root, custom: false },
            );
        }
    }
    if let Some(d) = dirs::data_dir() {
        for (n, shown) in YUZU_FORKS {
            push(&mut out, Place { kind: Kind::Yuzu, name: shown.into(), root: d.join(n), custom: false });
        }
    }
    if let Some(h) = &home {
        for app in sorted_dirs(&h.join(".var/app")) {
            for (n, shown) in YUZU_FORKS {
                let root = app.join("data").join(n);
                push(&mut out, Place { kind: Kind::Yuzu, name: trf("{} (Flatpak)", &[&shown]), root, custom: false });
            }
        }
    }
    for d in drive_roots().into_iter().filter(|d| d.join("atmosphere").is_dir()) {
        let label = d.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_else(|| d.display().to_string());
        push(&mut out, Place { kind: Kind::SdCard, name: trf("SD card ({})", &[&label]), root: d, custom: false });
    }
    // only what exists, except the main Ryujinx (shown as "not found")
    out.retain(|p| p.found() || (p.kind == Kind::Ryujinx && p.name == "Ryujinx"));
    for c in custom {
        let name = match c.kind {
            Kind::Ryujinx => tr("Ryujinx (portable)"),
            Kind::Yuzu => tr("yuzu family (folder)"),
            Kind::Recomp => "MHGU PC Recomp".to_string(),
            Kind::SdCard => trf("SD card ({})", &[&c.path.display()]),
            Kind::Folder => c
                .path
                .file_name()
                .map(|n| n.to_string_lossy().into_owned())
                .unwrap_or_else(|| c.path.display().to_string()),
        };
        push(&mut out, Place { kind: c.kind, name, root: c.path.clone(), custom: true });
    }
    out
}

/// The kind of place a picked folder is: a Ryujinx data folder (`mods/` + `bis/` or `Config.json`), a yuzu-family
/// data folder (`nand/` or `load/`), the recomp's folder, an SD card (`atmosphere/`), else a plain folder.
pub fn kind_of_folder(p: &Path) -> Kind {
    if p.join("atmosphere").is_dir() {
        Kind::SdCard
    } else if is_recomp_folder(p) {
        Kind::Recomp
    } else if p.join("Config.json").is_file() || (p.join("bis").is_dir() && p.join("mods").is_dir()) {
        Kind::Ryujinx
    } else if p.join("nand").is_dir() || p.join("load").is_dir() {
        Kind::Yuzu
    } else {
        Kind::Folder
    }
}

/// Process names of the Switch emulators and the recomp (lower case prefixes).
pub const EMULATORS: [&str; 9] =
    ["ryujinx", "ryubing", "yuzu", "suyu", "sudachi", "citron", "eden", "torzu", "mhgurecomp"];

/// The emulators running now (their process names): the game must be closed while its files change.
pub fn running_emulators() -> Vec<String> {
    use sysinfo::{ProcessRefreshKind, RefreshKind, System};
    let sys = System::new_with_specifics(RefreshKind::nothing().with_processes(ProcessRefreshKind::nothing()));
    let mut found: Vec<String> = sys
        .processes()
        .values()
        .map(|p| p.name().to_string_lossy().into_owned())
        .filter(|n| EMULATORS.iter().any(|e| n.to_lowercase().starts_with(e)))
        .collect();
    found.sort();
    found.dedup();
    found
}

#[cfg(test)]
mod tests {
    use super::*;

    fn place(kind: Kind, root: &str) -> Place {
        Place { kind, name: String::new(), root: PathBuf::from(root), custom: true }
    }

    #[test]
    fn each_place_has_its_mod_folder() {
        let m = "MHGU Definitive Edition";
        assert_eq!(
            place(Kind::Ryujinx, "/r").layout(m),
            Layout::ModFolder(PathBuf::from("/r/mods/contents/0100770008dd8000/MHGU Definitive Edition"))
        );
        assert_eq!(
            place(Kind::Folder, "/f").record_path(m),
            PathBuf::from("/f/MHGU Definitive Edition/mhgu-de-install.json")
        );
        // a yuzu folder without qt-config.ini: <data>/load
        let d = std::env::temp_dir().join(format!("mhgu-de-places-{}", std::process::id()));
        let y = d.join("eden-mhgu-de-test"); // no such folder in ~/.config: only its own qt-config.ini counts
        std::fs::create_dir_all(y.join("config")).unwrap();
        assert_eq!(
            place(Kind::Yuzu, y.to_str().unwrap()).layout(m),
            Layout::ModFolder(y.join("load/0100770008DD8000/MHGU Definitive Edition"))
        );
        std::fs::write(
            y.join("config/qt-config.ini"),
            "[Data%20Storage]\nload_directory\\default=false\nload_directory=/games/load\n",
        )
        .unwrap();
        assert_eq!(
            place(Kind::Yuzu, y.to_str().unwrap()).layout(m),
            Layout::ModFolder(PathBuf::from("/games/load/0100770008DD8000/MHGU Definitive Edition"))
        );
        std::fs::remove_dir_all(&d).unwrap();
    }

    #[test]
    fn sd_card_files_go_to_atmosphere_folders() {
        let p = place(Kind::SdCard, "/sd");
        let m = "MHGU Definitive Edition";
        assert_eq!(
            p.target(m, "exefs/subsdk1"),
            PathBuf::from("/sd/atmosphere/contents/0100770008DD8000/exefs/subsdk1")
        );
        assert_eq!(
            p.target(m, "exefs/FB08F1D2.ips"),
            PathBuf::from("/sd/atmosphere/exefs_patches/MHGU Definitive Edition/FB08F1D2.ips")
        );
        assert_eq!(
            p.target(m, "romfs/nativeNX/mhgu_de/a.bin"),
            PathBuf::from("/sd/atmosphere/contents/0100770008DD8000/romfs/nativeNX/mhgu_de/a.bin")
        );
        assert_eq!(p.record_path(m), PathBuf::from("/sd/atmosphere/contents/0100770008DD8000/mhgu-de-install.json"));
    }

    #[test]
    fn a_picked_folder_is_recognised() {
        let d = std::env::temp_dir().join(format!("mhgu-de-kind-{}", std::process::id()));
        for (sub, kind) in [("atmosphere", Kind::SdCard), ("nand", Kind::Yuzu), ("bis", Kind::Folder)] {
            let f = d.join(sub.to_string() + "-case");
            std::fs::create_dir_all(f.join(sub)).unwrap();
            assert_eq!(kind_of_folder(&f), kind, "{sub}");
        }
        let f = d.join("recomp");
        std::fs::create_dir_all(&f).unwrap();
        std::fs::write(f.join("mhgurecomp"), "").unwrap();
        assert_eq!(kind_of_folder(&f), Kind::Recomp);
        std::fs::remove_dir_all(&d).unwrap();
    }
}
