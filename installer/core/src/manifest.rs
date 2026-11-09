//! `manifest.json`, the release asset tools/release.py writes (schema 1): the release, every package (core, monsters,
//! maps, later shared utility packages) with its zip, size, sha256, requirements and every file it installs.

use crate::i18n::{tr, trf};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeSet, HashMap};

/// The newest manifest schema this installer reads; a newer one asks for an installer update.
pub const SCHEMA: u32 = 1;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Kind {
    /// The module and every monster's data file: always installed.
    Core,
    /// A monster the player ticks.
    Monster,
    /// A ported arena, installed with the monsters that require it.
    Map,
    /// Any other package a monster requires (shared utilities, later): installed like a map.
    #[serde(other)]
    Utility,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct FileEntry {
    /// Below the mod folder: `exefs/...` or `romfs/...`
    pub path: String,
    pub size: u64,
    pub sha256: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Package {
    pub name: String,
    pub kind: Kind,
    pub title: String,
    #[serde(default)]
    pub subtitle: String,
    pub version: String,
    pub zip: String,
    pub size: u64,
    pub sha256: String,
    #[serde(default)]
    pub requires: Vec<String>,
    #[serde(default)]
    pub requires_core: Option<String>,
    /// A map's stage folder (m<folder>).
    #[serde(default)]
    pub folder: Option<u32>,
    /// A monster package's allocations.toml entries (Dalamadur: four).
    #[serde(default)]
    pub entries: Vec<String>,
    /// Its picture in the release's icons zip.
    #[serde(default)]
    pub icon: Option<String>,
    pub files: Vec<FileEntry>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Manifest {
    pub schema: u32,
    pub release: String,
    #[serde(default)]
    pub prerelease: bool,
    pub installer_min: String,
    pub title_id: String,
    pub mod_folder: String,
    #[serde(default)]
    pub icons: Option<String>,
    pub packages: Vec<Package>,
    /// Save migration steps (filled once the installer migrates saves).
    #[serde(default)]
    pub migrations: Vec<serde_json::Value>,
    /// Per package: its item / gear IDs, for the save cleaning on removal.
    #[serde(default)]
    pub cleaning: serde_json::Map<String, serde_json::Value>,
    /// Release-specific warnings, shown in the review popup.
    #[serde(default)]
    pub warnings: Vec<String>,
}

/// A path the installer may write: relative, below `exefs/` or `romfs/`, plain components only.
pub fn safe_path(p: &str) -> bool {
    let mut parts = p.split('/');
    matches!(parts.next(), Some("exefs") | Some("romfs"))
        && !p.contains('\\')
        && !p.contains(':')
        && p.split('/').count() >= 2
        && p.split('/').all(|c| !c.is_empty() && c != "." && c != ".." && !c.chars().any(|ch| ch.is_control()))
}

fn safe_name(s: &str) -> bool {
    !s.is_empty()
        && s != "."
        && s != ".."
        && !s.chars().any(|c| matches!(c, '/' | '\\' | ':' | '*' | '?' | '"' | '<' | '>' | '|') || c.is_control())
}

impl Manifest {
    /// Parse and check a manifest (`validate`).
    pub fn parse(bytes: &[u8]) -> Result<Manifest, String> {
        let probe: serde_json::Value =
            serde_json::from_slice(bytes).map_err(|e| trf("Unreadable manifest ({})", &[&e]))?;
        if probe.get("schema").and_then(|s| s.as_u64()).is_some_and(|s| s > SCHEMA as u64) {
            return Err(tr("This release needs a newer installer: update the installer first"));
        }
        let m: Manifest = serde_json::from_value(probe).map_err(|e| trf("Unreadable manifest ({})", &[&e]))?;
        m.validate()?;
        Ok(m)
    }

    pub fn validate(&self) -> Result<(), String> {
        let err = |what: String| Err(trf("Invalid manifest: {}", &[&what]));
        if self.packages.iter().filter(|p| p.kind == Kind::Core).count() != 1 {
            return err("one core package".into());
        }
        if !safe_name(&self.mod_folder)
            || self.title_id.len() != 16
            || !self.title_id.chars().all(|c| c.is_ascii_hexdigit())
        {
            return err("mod folder or title ID".into());
        }
        let names: BTreeSet<&str> = self.packages.iter().map(|p| p.name.as_str()).collect();
        if names.len() != self.packages.len() {
            return err("two packages with one name".into());
        }
        let mut owner: HashMap<&str, &str> = HashMap::new();
        for p in &self.packages {
            if !safe_name(&p.name) || !safe_name(&p.zip) {
                return err(format!("package name {:?}", p.name));
            }
            for r in &p.requires {
                match self.package(r) {
                    Some(q) if q.kind != Kind::Core && q.kind != Kind::Monster => {}
                    _ => return err(format!("{} requires {r}", p.name)),
                }
            }
            for f in &p.files {
                if !safe_path(&f.path) {
                    return err(format!("unsafe path {:?} in {}", f.path, p.name));
                }
                if let Some(o) = owner.insert(f.path.as_str(), p.name.as_str()) {
                    return err(format!("{} in both {o} and {}", f.path, p.name));
                }
            }
        }
        Ok(())
    }

    pub fn package(&self, name: &str) -> Option<&Package> {
        self.packages.iter().find(|p| p.name == name)
    }

    pub fn core(&self) -> &Package {
        self.packages.iter().find(|p| p.kind == Kind::Core).expect("validated: one core")
    }

    pub fn monsters(&self) -> impl Iterator<Item = &Package> {
        self.packages.iter().filter(|p| p.kind == Kind::Monster)
    }

    /// Every package that `wanted` (monster names) needs, the core first, then the dependencies before what needs
    /// them; unknown names are left out.
    pub fn closure(&self, wanted: &BTreeSet<String>) -> Vec<String> {
        fn add(m: &Manifest, n: &str, out: &mut Vec<String>) {
            let Some(p) = m.package(n) else { return };
            if out.iter().any(|o| o == n) {
                return;
            }
            for r in &p.requires {
                add(m, r, out);
            }
            out.push(n.to_string());
        }
        let mut out = vec![self.core().name.clone()];
        for p in self.monsters().filter(|p| wanted.contains(&p.name)) {
            add(self, &p.name, &mut out);
        }
        out
    }

    /// The monsters that require package `name` (a map: the monsters fought there), titles.
    pub fn needed_by(&self, name: &str) -> Vec<&Package> {
        self.monsters().filter(|p| p.requires.iter().any(|r| r == name)).collect()
    }
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;

    pub fn file(path: &str) -> FileEntry {
        FileEntry { path: path.into(), size: 1, sha256: "00".into() }
    }

    pub fn pkg(name: &str, kind: Kind, requires: &[&str], files: &[&str]) -> Package {
        Package {
            name: name.into(),
            kind,
            title: name.into(),
            subtitle: String::new(),
            version: "1.0.0".into(),
            zip: format!("{name}-1.0.0.zip"),
            size: 1,
            sha256: "00".into(),
            requires: requires.iter().map(|s| s.to_string()).collect(),
            requires_core: None,
            folder: None,
            entries: vec![],
            icon: None,
            files: files.iter().map(|f| file(f)).collect(),
        }
    }

    pub fn sample() -> Manifest {
        Manifest {
            schema: 1,
            release: "1.10.0".into(),
            prerelease: false,
            installer_min: "1.0.0".into(),
            title_id: "0100770008DD8000".into(),
            mod_folder: "MHGU Definitive Edition".into(),
            icons: None,
            packages: vec![
                pkg("core", Kind::Core, &[], &["exefs/subsdk1", "exefs/FB08.ips", "romfs/nativeNX/mhgu_de/a.bin"]),
                pkg("gogmazios", Kind::Monster, &["battlequarters"], &["romfs/nativeNX/arc/enemy/em089_00.arc"]),
                pkg("dalamadur", Kind::Monster, &["speartip_crag"], &["romfs/nativeNX/arc/enemy/em090_00.arc"]),
                pkg("shah", Kind::Monster, &["speartip_crag"], &["romfs/nativeNX/arc/enemy/em090_01.arc"]),
                pkg("monoblos", Kind::Monster, &[], &["romfs/nativeNX/arc/enemy/em007_01.arc"]),
                pkg("battlequarters", Kind::Map, &[], &["romfs/nativeNX/arc/stage/m28d/m28d.arc"]),
                pkg("speartip_crag", Kind::Map, &[], &["romfs/nativeNX/arc/stage/m29d/m29d.arc"]),
            ],
            migrations: vec![],
            cleaning: Default::default(),
            warnings: vec![],
        }
    }

    #[test]
    fn a_release_manifest_parses() {
        let json = serde_json::to_vec(&sample()).unwrap();
        let m = Manifest::parse(&json).unwrap();
        assert_eq!(m.core().name, "core");
        assert_eq!(m.monsters().count(), 4);
        // a kind this installer does not know is a dependency package
        let j = String::from_utf8(json).unwrap().replace("\"kind\":\"map\"", "\"kind\":\"shared\"");
        let m = Manifest::parse(j.as_bytes()).unwrap();
        assert_eq!(m.package("battlequarters").unwrap().kind, Kind::Utility);
    }

    #[test]
    fn a_newer_schema_asks_for_an_update() {
        let mut m = serde_json::to_value(sample()).unwrap();
        m["schema"] = 2.into();
        assert!(Manifest::parse(m.to_string().as_bytes()).unwrap_err().contains("newer installer"));
    }

    #[test]
    fn unsafe_paths_are_refused() {
        for p in ["../x", "romfs/../../x", "/romfs/x", "romfs\\x", "C:/x", "romfs", "romfs//x", "save/x", "exefs/./x"] {
            assert!(!safe_path(p), "{p}");
        }
        assert!(safe_path("romfs/nativeNX/arc/stage/m28d/m28d.arc") && safe_path("exefs/subsdk1"));
        let mut m = sample();
        m.packages[1].files.push(file("romfs/../../../.bashrc"));
        assert!(m.validate().is_err());
    }

    #[test]
    fn a_path_in_two_packages_or_a_missing_requirement_is_refused() {
        let mut m = sample();
        m.packages[4].files.push(file("romfs/nativeNX/arc/enemy/em089_00.arc"));
        assert!(m.validate().unwrap_err().contains("in both"));
        let mut m = sample();
        m.packages[1].requires.push("nowhere".into());
        assert!(m.validate().is_err());
        let mut m = sample();
        m.packages[1].requires = vec!["monoblos".into()];
        assert!(m.validate().is_err(), "a monster is not a requirement");
    }

    #[test]
    fn the_closure_brings_core_and_maps_once() {
        let m = sample();
        let w = |n: &[&str]| n.iter().map(|s| s.to_string()).collect::<BTreeSet<_>>();
        assert_eq!(m.closure(&w(&[])), ["core"]);
        assert_eq!(m.closure(&w(&["dalamadur", "shah", "nobody"])), ["core", "speartip_crag", "dalamadur", "shah"]);
        assert_eq!(m.needed_by("speartip_crag").len(), 2);
    }
}
