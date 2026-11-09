//! Doing a plan: download the zips (cache, size + sha256 against the manifest), then per place
//! - mod folder (emulators, recomp, folders): the new `MH4U Port` is built beside the old one (`.MH4U Port.new`:
//!   unchanged packages hard-linked or copied from the old folder, the others extracted), then swapped in by rename;
//!   the old folder stays until the swap worked, so a place is never half installed;
//! - SD card: our old files deleted, the new ones written, the record last (other mods share contents/<title>).
//!   Every extracted file is checked against the manifest (path, size, sha256); a zip member outside the package's
//!   files is refused.

use crate::i18n::{tr, trf};
use crate::manifest::{Manifest, Package};
use crate::places::{Layout, Place, TITLE_ID};
use crate::plan::{Action, PlacePlan, plan};
use crate::record::{self, State};
use crate::source::{Release, Source, hex, sha256_file};
use crate::zipread;
use sha2::{Digest, Sha256};
use std::collections::{BTreeSet, HashMap};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};

/// The plan of one place for `wanted`, with its state; a recorded package whose files are missing or changed size
/// is planned as an update to the same version (a repair).
pub fn plan_for(place: &Place, m: &Manifest, wanted: &BTreeSet<String>, remove_all: bool) -> (State, PlacePlan) {
    let mut state = record::read(place, &m.mod_folder);
    if let State::Recorded(r) = &mut state {
        for i in r.packages.values_mut() {
            let ok = i.files.iter().all(|f| {
                std::fs::metadata(place.target(&m.mod_folder, &f.path))
                    .is_ok_and(|md| md.is_file() && md.len() == f.size)
            });
            if !ok {
                i.files.clear();
            }
        }
    }
    let p = plan(m, wanted, &state, remove_all);
    (state, p)
}

fn cancelled(cancel: &AtomicBool) -> Result<(), String> {
    if cancel.load(Ordering::Relaxed) { Err(tr("Cancelled")) } else { Ok(()) }
}

/// The zips of `names`, downloaded into `cache/<release>/` unless already there with the right size and sha256;
/// `progress(package, done, total)`.
pub fn fetch(
    src: &Source,
    rel: &Release,
    m: &Manifest,
    names: &[String],
    cache: &Path,
    progress: &dyn Fn(&str, u64, u64),
    cancel: &AtomicBool,
) -> Result<HashMap<String, PathBuf>, String> {
    let dir = cache.join(&m.release);
    let mut out = HashMap::new();
    for n in names {
        let p = m.package(n).ok_or_else(|| trf("{} is not in this release", &[n]))?;
        let to = dir.join(&p.zip);
        let cached =
            std::fs::metadata(&to).is_ok_and(|md| md.len() == p.size) && sha256_file(&to).is_ok_and(|h| h == p.sha256);
        if !cached {
            cancelled(cancel)?;
            let a = rel.asset(&p.zip).ok_or_else(|| trf("The release has no {}", &[&p.zip]))?;
            let got = src.download(a, &to, &|d, t| progress(n, d, t), cancel)?;
            if got != p.sha256 || std::fs::metadata(&to).map(|m| m.len()).unwrap_or(0) != p.size {
                let _ = std::fs::remove_file(&to);
                return Err(trf("The download of {} does not match the release's checksum", &[&p.zip]));
            }
        }
        progress(n, p.size, p.size);
        out.insert(n.clone(), to);
    }
    Ok(out)
}

fn write_file(to: &Path, data: &[u8]) -> Result<(), String> {
    let err = |e: std::io::Error| trf("Could not write {} ({})", &[&to.display(), &e]);
    if let Some(d) = to.parent() {
        std::fs::create_dir_all(d).map_err(err)?;
    }
    let tmp = to.with_file_name(format!(".{}.part", to.file_name().map(|n| n.to_string_lossy()).unwrap_or_default()));
    std::fs::write(&tmp, data).map_err(err)?;
    std::fs::rename(&tmp, to).map_err(|e| {
        let _ = std::fs::remove_file(&tmp);
        err(e)
    })
}

/// Extract package `p` from its zip: every member must be one of its manifest files (path, size, sha256), each
/// written to `dest(path)`; every manifest file must be there.
fn extract(
    m: &Manifest,
    p: &Package,
    zip: &Path,
    dest: &dyn Fn(&str) -> PathBuf,
    cancel: &AtomicBool,
) -> Result<(), String> {
    let z = std::fs::read(zip).map_err(|e| trf("Could not read {} ({})", &[&zip.display(), &e]))?;
    let mut want: HashMap<&str, &crate::manifest::FileEntry> = p.files.iter().map(|f| (f.path.as_str(), f)).collect();
    let prefix = format!("{}/", m.mod_folder);
    for e in zipread::entries(&z)? {
        cancelled(cancel)?;
        if e.name.ends_with('/') {
            continue;
        }
        let rel = e.name.strip_prefix(&prefix).unwrap_or("");
        let f =
            want.remove(rel).ok_or_else(|| trf("{} holds {}, which its release does not list", &[&p.zip, &e.name]))?;
        if e.size != f.size {
            return Err(trf("{} in {} does not match the release", &[&rel, &p.zip]));
        }
        let data = zipread::read(&z, &e)?;
        if hex(&Sha256::digest(&data)) != f.sha256 {
            return Err(trf("{} in {} does not match the release", &[&rel, &p.zip]));
        }
        write_file(&dest(rel), &data)?;
    }
    if let Some(miss) = want.keys().next() {
        return Err(trf("{} lacks {}", &[&p.zip, miss]));
    }
    Ok(())
}

/// Do `plan` in `place` (planned from `state`) with the fetched `zips`; `progress(package, done, total)` counts the
/// packages of this place.
pub fn install(
    place: &Place,
    m: &Manifest,
    state: &State,
    plan: &PlacePlan,
    zips: &HashMap<String, PathBuf>,
    progress: &dyn Fn(&str, u64, u64),
    cancel: &AtomicBool,
) -> Result<(), String> {
    if let State::Unreadable(why) = state {
        return Err(why.clone());
    }
    match place.layout(&m.mod_folder) {
        Layout::ModFolder(dir) => install_folder(&dir, m, plan, zips, progress, cancel),
        Layout::Atmosphere(root) => install_sd(place, &root, m, state, plan, zips, progress, cancel),
    }
}

fn link_or_copy(from: &Path, to: &Path) -> Result<(), String> {
    let err = |e: std::io::Error| trf("Could not copy {} ({})", &[&from.display(), &e]);
    if let Some(d) = to.parent() {
        std::fs::create_dir_all(d).map_err(err)?;
    }
    if std::fs::hard_link(from, to).is_ok() {
        return Ok(());
    }
    std::fs::copy(from, to).map(drop).map_err(err)
}

fn remove_tree(p: &Path) -> Result<(), String> {
    match std::fs::remove_dir_all(p) {
        Err(e) if e.kind() != std::io::ErrorKind::NotFound => Err(trf("Could not remove {} ({})", &[&p.display(), &e])),
        _ => Ok(()),
    }
}

fn install_folder(
    dir: &Path,
    m: &Manifest,
    plan: &PlacePlan,
    zips: &HashMap<String, PathBuf>,
    progress: &dyn Fn(&str, u64, u64),
    cancel: &AtomicBool,
) -> Result<(), String> {
    let parent = dir.parent().ok_or_else(|| tr("The mod folder has no parent folder"))?;
    let name = dir.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
    let (staging, old) = (parent.join(format!(".{name}.new")), parent.join(format!(".{name}.old")));
    if plan.keep.is_empty() {
        // everything leaves: aside first (a file in use fails before anything is lost), then deleted
        if dir.exists() {
            remove_tree(&old)?;
            std::fs::rename(dir, &old).map_err(|e| trf("Could not remove {} ({})", &[&dir.display(), &e]))?;
            remove_tree(&old)?;
        }
        return Ok(());
    }
    remove_tree(&staging)?;
    let extract_set: BTreeSet<String> = plan.to_extract().into_iter().collect();
    let res = (|| {
        let total = plan.keep.len() as u64;
        for (k, n) in plan.keep.iter().enumerate() {
            cancelled(cancel)?;
            let p = m.package(n).ok_or_else(|| trf("{} is not in this release", &[n]))?;
            progress(n, k as u64, total);
            if extract_set.contains(n) {
                let zip = zips.get(n).ok_or_else(|| trf("{} was not downloaded", &[n]))?;
                extract(m, p, zip, &|rel| staging.join(rel), cancel)?;
            } else {
                for f in &p.files {
                    link_or_copy(&dir.join(&f.path), &staging.join(&f.path))?;
                }
            }
        }
        record::write(&staging.join(record::FILE), &record::of(m, &plan.keep))?;
        cancelled(cancel)?;
        // the swap: old aside, new in, old deleted
        remove_tree(&old)?;
        let had = dir.exists();
        if had {
            std::fs::rename(dir, &old).map_err(|e| trf("Could not replace {} ({})", &[&dir.display(), &e]))?;
        }
        if let Err(e) = std::fs::rename(&staging, dir) {
            if had {
                let _ = std::fs::rename(&old, dir);
            }
            return Err(trf("Could not replace {} ({})", &[&dir.display(), &e]));
        }
        progress("", total, total);
        Ok(())
    })();
    if res.is_err() {
        let _ = std::fs::remove_dir_all(&staging);
    }
    let _ = std::fs::remove_dir_all(&old);
    res
}

/// Delete a file and the folders it leaves empty, up to (not including) `stop`.
fn delete_pruning(f: &Path, stop: &Path) -> Result<(), String> {
    match std::fs::remove_file(f) {
        Err(e) if e.kind() != std::io::ErrorKind::NotFound => {
            return Err(trf("Could not remove {} ({})", &[&f.display(), &e]));
        }
        _ => {}
    }
    let mut d = f.parent();
    while let Some(p) = d {
        if p == stop || !p.starts_with(stop) || std::fs::remove_dir(p).is_err() {
            break;
        }
        d = p.parent();
    }
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn install_sd(
    place: &Place,
    root: &Path,
    m: &Manifest,
    state: &State,
    plan: &PlacePlan,
    zips: &HashMap<String, PathBuf>,
    progress: &dyn Fn(&str, u64, u64),
    cancel: &AtomicBool,
) -> Result<(), String> {
    let mf = &m.mod_folder;
    let stop = root.join("atmosphere");
    let contents = stop.join("contents").join(TITLE_ID);
    // 1. our old files leave
    let mut old: Vec<String> = vec![];
    if plan.replace_hand_install {
        old.extend(m.packages.iter().flat_map(|p| p.files.iter().map(|f| f.path.clone())));
        remove_tree(&contents.join("romfs/nativeNX/mh4uport"))?;
        remove_tree(&stop.join("exefs_patches").join(mf))?;
    } else if let Some(r) = state.record() {
        for c in plan.changes.iter().filter(|c| !matches!(c.action, Action::Add)) {
            if let Some(i) = r.packages.get(&c.package) {
                old.extend(i.files.iter().map(|f| f.path.clone()));
            }
        }
    }
    for rel in &old {
        cancelled(cancel)?;
        delete_pruning(&place.target(mf, rel), &stop)?;
    }
    // 2. the new ones
    let todo = plan.to_extract();
    let total = todo.len() as u64;
    for (k, n) in todo.iter().enumerate() {
        progress(n, k as u64, total);
        let p = m.package(n).ok_or_else(|| trf("{} is not in this release", &[n]))?;
        let zip = zips.get(n).ok_or_else(|| trf("{} was not downloaded", &[n]))?;
        extract(m, p, zip, &|rel| place.target(mf, rel), cancel)?;
    }
    // 3. the record, last
    let rp = place.record_path(mf);
    if plan.keep.is_empty() {
        delete_pruning(&rp, &stop)?;
    } else {
        record::write(&rp, &record::of(m, &plan.keep))?;
    }
    progress("", total, total);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::manifest::FileEntry;
    use crate::places::Kind as PlaceKind;

    /// A fake release: each package's files hold their own path, zipped as tools/release.py does.
    pub fn fake(dir: &Path) -> Manifest {
        let mut m = crate::manifest::tests::sample();
        std::fs::create_dir_all(dir).unwrap();
        for p in &mut m.packages {
            let mut members: Vec<(String, Vec<u8>)> = vec![];
            for f in &mut p.files {
                let data = format!("{} {}", p.name, f.path).into_bytes();
                *f = FileEntry { path: f.path.clone(), size: data.len() as u64, sha256: hex(&Sha256::digest(&data)) };
                members.push((format!("MH4U Port/{}", f.path), data));
            }
            let refs: Vec<(&str, &[u8])> = members.iter().map(|(n, d)| (n.as_str(), d.as_slice())).collect();
            let z = zipread::write(&refs);
            std::fs::write(dir.join(&p.zip), &z).unwrap();
            p.size = z.len() as u64;
            p.sha256 = hex(&Sha256::digest(&z));
        }
        m
    }

    fn tmp(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("mh4u-apply-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    fn set(n: &[&str]) -> BTreeSet<String> {
        n.iter().map(|s| s.to_string()).collect()
    }

    fn run(place: &Place, m: &Manifest, zips: &Path, wanted: &[&str], all: bool) -> PlacePlan {
        let (state, p) = plan_for(place, m, &set(wanted), all);
        let z: HashMap<String, PathBuf> = m.packages.iter().map(|p| (p.name.clone(), zips.join(&p.zip))).collect();
        install(place, m, &state, &p, &z, &|_, _, _| {}, &AtomicBool::new(false)).unwrap();
        p
    }

    fn files(d: &Path) -> Vec<String> {
        let mut out = vec![];
        let mut stack = vec![d.to_path_buf()];
        while let Some(x) = stack.pop() {
            for e in std::fs::read_dir(&x).into_iter().flatten().flatten() {
                if e.path().is_dir() {
                    stack.push(e.path());
                } else {
                    out.push(e.path().strip_prefix(d).unwrap().to_string_lossy().replace('\\', "/"));
                }
            }
        }
        out.sort();
        out
    }

    #[test]
    fn a_folder_place_installs_updates_and_removes() {
        let d = tmp("folder");
        let m = fake(&d.join("zips"));
        let place = Place { kind: PlaceKind::Folder, name: String::new(), root: d.join("mods"), custom: true };
        run(&place, &m, &d.join("zips"), &["gogmazios"], false);
        let got = files(&d.join("mods/MH4U Port"));
        assert!(got.contains(&"romfs/nativeNX/arc/stage/m28d/m28d.arc".to_string()), "the map came along");
        assert!(got.contains(&"mh4uport-install.json".to_string()));
        assert_eq!(files(&d.join("mods")).iter().filter(|f| f.starts_with('.')).count(), 0, "no staging left");
        // swap Gogmazios for Monoblos: his map leaves with him
        let p = run(&place, &m, &d.join("zips"), &["monoblos"], false);
        assert_eq!(p.to_extract(), ["monoblos"]);
        let got = files(&d.join("mods/MH4U Port"));
        assert!(!got.iter().any(|f| f.contains("m28d") || f.contains("em089")));
        assert!(got.contains(&"romfs/nativeNX/arc/enemy/em007_01.arc".to_string()));
        // a deleted file is repaired
        std::fs::remove_file(d.join("mods/MH4U Port/romfs/nativeNX/arc/enemy/em007_01.arc")).unwrap();
        let p = run(&place, &m, &d.join("zips"), &["monoblos"], false);
        assert_eq!(p.changes[0].action, Action::Update { from: "1.0.0".into() });
        assert!(d.join("mods/MH4U Port/romfs/nativeNX/arc/enemy/em007_01.arc").is_file());
        assert!(plan_for(&place, &m, &set(&["monoblos"]), false).1.is_empty());
        run(&place, &m, &d.join("zips"), &[], true);
        assert!(!d.join("mods/MH4U Port").exists());
        std::fs::remove_dir_all(&d).unwrap();
    }

    #[test]
    fn a_hand_install_is_replaced_whole() {
        let d = tmp("hand");
        let m = fake(&d.join("zips"));
        let place = Place { kind: PlaceKind::Folder, name: String::new(), root: d.join("mods"), custom: true };
        std::fs::create_dir_all(d.join("mods/MH4U Port/romfs/old")).unwrap();
        std::fs::write(d.join("mods/MH4U Port/romfs/old/leftover.arc"), "x").unwrap();
        let p = run(&place, &m, &d.join("zips"), &["monoblos"], false);
        assert!(p.replace_hand_install);
        assert!(!d.join("mods/MH4U Port/romfs/old").exists());
        assert!(matches!(record::read(&place, "MH4U Port"), State::Recorded(_)));
        std::fs::remove_dir_all(&d).unwrap();
    }

    #[test]
    fn an_sd_card_keeps_other_mods() {
        let d = tmp("sd");
        let m = fake(&d.join("zips"));
        let place = Place { kind: PlaceKind::SdCard, name: String::new(), root: d.join("sd"), custom: true };
        let other = d.join("sd/atmosphere/contents/0100770008DD8000/romfs/other_mod/file.bin");
        std::fs::create_dir_all(other.parent().unwrap()).unwrap();
        std::fs::write(&other, "theirs").unwrap();
        run(&place, &m, &d.join("zips"), &["gogmazios"], false);
        let a = d.join("sd/atmosphere");
        assert!(a.join("exefs_patches/MH4U Port/FB08.ips").is_file());
        assert!(a.join("contents/0100770008DD8000/exefs/subsdk1").is_file());
        assert!(a.join("contents/0100770008DD8000/romfs/nativeNX/arc/stage/m28d/m28d.arc").is_file());
        run(&place, &m, &d.join("zips"), &[], true);
        assert!(other.is_file(), "another mod's file stays");
        let left = files(&a);
        assert_eq!(left, ["contents/0100770008DD8000/romfs/other_mod/file.bin"], "nothing of ours is left");
        std::fs::remove_dir_all(&d).unwrap();
    }

    #[test]
    fn a_zip_that_does_not_match_its_manifest_is_refused() {
        let d = tmp("bad");
        let m = fake(&d.join("zips"));
        let place = Place { kind: PlaceKind::Folder, name: String::new(), root: d.join("mods"), custom: true };
        // a member the manifest does not list (a path that would escape is never listed: manifest.rs safe_path)
        let z = zipread::write(&[("MH4U Port/romfs/x.arc", b"x"), ("MH4U Port/../../escape", b"x")]);
        std::fs::write(d.join("zips/monoblos-1.0.0.zip"), z).unwrap();
        let (state, p) = plan_for(&place, &m, &set(&["monoblos"]), false);
        let zips: HashMap<String, PathBuf> =
            m.packages.iter().map(|p| (p.name.clone(), d.join("zips").join(&p.zip))).collect();
        let e = install(&place, &m, &state, &p, &zips, &|_, _, _| {}, &AtomicBool::new(false)).unwrap_err();
        assert!(e.contains("does not list"), "{e}");
        assert!(!d.join("mods/MH4U Port").exists() && !d.join("escape").exists(), "nothing installed, nothing escaped");
        assert!(files(&d.join("mods")).is_empty(), "no staging left");
        std::fs::remove_dir_all(&d).unwrap();
    }

    #[test]
    fn fetch_uses_the_cache_and_checks_downloads() {
        let d = tmp("fetch");
        let m = fake(&d.join("rel/v1.10.0"));
        let assets: Vec<String> = m
            .packages
            .iter()
            .map(|p| format!(r#"{{"name":"{}","browser_download_url":"v1.10.0/{}","size":{}}}"#, p.zip, p.zip, p.size))
            .collect();
        std::fs::write(
            d.join("rel/releases.json"),
            format!(r#"[{{"tag_name":"v1.10.0","assets":[{}]}}]"#, assets.join(",")),
        )
        .unwrap();
        let src = Source::Local(d.join("rel"));
        let rel = src.releases().unwrap().remove(0);
        let names = vec!["core".to_string(), "monoblos".to_string()];
        let z = fetch(&src, &rel, &m, &names, &d.join("cache"), &|_, _, _| {}, &AtomicBool::new(false)).unwrap();
        assert!(z["core"].starts_with(d.join("cache/1.10.0")));
        // cached: works without the release files
        std::fs::remove_dir_all(d.join("rel/v1.10.0")).unwrap();
        fetch(&src, &rel, &m, &names, &d.join("cache"), &|_, _, _| {}, &AtomicBool::new(false)).unwrap();
        // a changed cached file is downloaded again, and the broken download refused
        std::fs::write(&z["core"], "tampered").unwrap();
        assert!(fetch(&src, &rel, &m, &names, &d.join("cache"), &|_, _, _| {}, &AtomicBool::new(false)).is_err());
        std::fs::remove_dir_all(&d).unwrap();
    }
}
