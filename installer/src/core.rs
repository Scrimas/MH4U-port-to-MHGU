//! Install logic shared by the window and the command line: mod-folder targets, the release manifest
//! (tools/release.py), package download + check, and the install record that updates and uninstalls use.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fs;
use std::io::{Read, Write};
use std::path::{Component, Path, PathBuf};

pub const TITLE_ID: &str = "0100770008DD8000";
/// GitHub repository whose latest release is installed (set MH4UPORT_REPO at build time to change it)
pub const DEFAULT_REPO: &str = match option_env!("MH4UPORT_REPO") {
    Some(r) => r,
    None => "Scrimas/MH4U_MHGU_port",
};
const RECORD: &str = "mh4uport-install.json";

#[derive(Deserialize, Clone, Debug)]
pub struct Package {
    pub name: String,
    #[serde(default)]
    pub title: String,
    pub version: String,
    #[serde(default)]
    pub requires_core: String,
    pub file: String,
    pub sha256: String,
    pub size: u64,
}

#[derive(Deserialize, Clone, Debug)]
pub struct Manifest {
    pub format: u32,
    pub title_id: String,
    pub mod_name: String,
    pub core: Package,
    pub monsters: Vec<Package>,
    #[serde(default)]
    pub warnings: Vec<String>,
}

#[derive(Clone, Copy, PartialEq, Debug)]
pub enum Layout {
    /// emulator mod folder of the title: <dir>/<mod name>/{exefs,romfs} (Ryujinx, the yuzu family)
    ModFolder,
    /// SD card root: atmosphere/contents/<title>/{exefs,romfs} + atmosphere/exefs_patches/<mod name>/*.ips
    Atmosphere,
}

#[derive(Clone, Debug)]
pub struct Target {
    pub label: String,
    pub dir: PathBuf,
    pub layout: Layout,
}

#[derive(Serialize, Deserialize, Default, Clone, Debug)]
pub struct Installed {
    pub version: String,
    /// installed files, relative to the target dir, '/' separated
    pub files: Vec<String>,
}

#[derive(Serialize, Deserialize, Default, Debug)]
pub struct Record {
    #[serde(default)]
    pub core: Option<Installed>,
    #[serde(default)]
    pub monsters: BTreeMap<String, Installed>,
}

fn vtuple(v: &str) -> Vec<u64> {
    v.split('.').map(|x| x.parse().unwrap_or(0)).collect()
}

impl Target {
    /// a folder the user picked: an SD card root (has 'atmosphere') or the title's mod folder
    pub fn custom(dir: &Path) -> Target {
        let layout = if dir.join("atmosphere").is_dir() { Layout::Atmosphere } else { Layout::ModFolder };
        Target { label: dir.display().to_string(), dir: dir.to_path_buf(), layout }
    }

    /// relative destination of a package path ("exefs/..." or "romfs/...") under the target dir
    fn rel_dest(&self, mod_name: &str, zpath: &str) -> String {
        match self.layout {
            Layout::ModFolder => format!("{mod_name}/{zpath}"),
            Layout::Atmosphere => match zpath.strip_prefix("exefs/") {
                Some(f) if f.ends_with(".ips") => format!("atmosphere/exefs_patches/{mod_name}/{f}"),
                _ => format!("atmosphere/contents/{TITLE_ID}/{zpath}"),
            },
        }
    }

    fn record_path(&self, mod_name: &str) -> PathBuf {
        match self.layout {
            Layout::ModFolder => self.dir.join(mod_name).join(RECORD),
            Layout::Atmosphere => self.dir.join("atmosphere/contents").join(TITLE_ID).join(RECORD),
        }
    }

    pub fn record(&self, mod_name: &str) -> Record {
        fs::read(self.record_path(mod_name))
            .ok()
            .and_then(|d| serde_json::from_slice(&d).ok())
            .unwrap_or_default()
    }

    fn save_record(&self, mod_name: &str, rec: &Record) -> Result<(), String> {
        let p = self.record_path(mod_name);
        if rec.core.is_none() && rec.monsters.is_empty() {
            let _ = fs::remove_file(&p);
            return Ok(());
        }
        fs::create_dir_all(p.parent().unwrap()).map_err(|e| e.to_string())?;
        fs::write(&p, serde_json::to_vec_pretty(rec).unwrap()).map_err(|e| format!("{}: {e}", p.display()))
    }
}

/// emulator mod folders found on this machine (the folder need not exist yet, only the emulator's data dir)
pub fn detect() -> Vec<Target> {
    let mut out: Vec<Target> = Vec::new();
    let home = dirs::home_dir().unwrap_or_default();
    let tid_l = TITLE_ID.to_lowercase();
    let ryujinx = |base: PathBuf| (base.clone(), base.join("mods/contents").join(&tid_l));
    let yuzu = |base: PathBuf| (base.clone(), base.join("load").join(TITLE_ID));
    let forks = ["yuzu", "suyu", "sudachi", "citron", "eden"];
    let mut roots: Vec<(String, PathBuf, PathBuf)> = Vec::new();
    if cfg!(windows) {
        if let Some(appdata) = dirs::config_dir() {          // %APPDATA%
            let (b, d) = ryujinx(appdata.join("Ryujinx"));
            roots.push(("Ryujinx".into(), b, d));
            for f in forks {
                let (b, d) = yuzu(appdata.join(f));
                roots.push((f.into(), b, d));
            }
        }
    } else {
        let config = dirs::config_dir().unwrap_or_else(|| home.join(".config"));
        let data = dirs::data_dir().unwrap_or_else(|| home.join(".local/share"));
        let (b, d) = ryujinx(config.join("Ryujinx"));
        roots.push(("Ryujinx".into(), b, d));
        for app in ["io.github.ryubing.Ryujinx", "org.ryujinx.Ryujinx"] {
            let (b, d) = ryujinx(home.join(".var/app").join(app).join("config/Ryujinx"));
            roots.push(("Ryujinx (Flatpak)".into(), b, d));
        }
        for f in forks {
            let (b, d) = yuzu(data.join(f));
            roots.push((f.into(), b, d));
        }
    }
    for f in ["yuzu", "suyu", "citron", "eden"] {           // EmuDeck keeps emulator data in Emulation/storage
        let (b, d) = yuzu(home.join("Emulation/storage").join(f));
        roots.push((format!("{f} (EmuDeck)"), b, d));
    }
    let (b, d) = ryujinx(home.join("Emulation/storage/ryujinx"));
    roots.push(("Ryujinx (EmuDeck)".into(), b, d));
    let mut seen: Vec<PathBuf> = Vec::new();             // EmuDeck's storage folders may be links to the same dirs
    for (label, base, dir) in roots {
        let Ok(canon) = fs::canonicalize(&base) else { continue };
        if !canon.is_dir() || seen.contains(&canon) {
            continue;
        }
        seen.push(canon);
        out.push(Target { label: format!("{label}: {}", dir.display()), dir, layout: Layout::ModFolder });
    }
    // SD cards with Atmosphère
    let mut sd: Vec<PathBuf> = Vec::new();
    if cfg!(windows) {
        for c in b'D'..=b'Z' {
            sd.push(PathBuf::from(format!("{}:\\", c as char)));
        }
    } else if let Some(user) = home.file_name() {
        for media in [Path::new("/run/media").join(user), Path::new("/media").join(user)] {
            if let Ok(rd) = fs::read_dir(media) {
                sd.extend(rd.flatten().map(|e| e.path()));
            }
        }
    }
    for root in sd {
        if root.join("atmosphere").is_dir() {
            out.push(Target { label: format!("Atmosphère SD card: {}", root.display()), dir: root, layout: Layout::Atmosphere });
        }
    }
    out
}

/// where the release comes from: the latest GitHub release, or a local folder (tests, offline installs)
pub enum Source {
    Github { repo: String, tag: String, assets: BTreeMap<String, String> },
    Local(PathBuf),
}

fn agent() -> ureq::Agent {
    ureq::Agent::config_builder().user_agent("mh4uport-installer").build().into()
}

impl Source {
    pub fn github_latest(repo: &str) -> Result<Source, String> {
        let url = format!("https://api.github.com/repos/{repo}/releases/latest");
        let mut r = agent()
            .get(&url)
            .header("Accept", "application/vnd.github+json")
            .call()
            .map_err(|e| format!("{url}: {e}"))?;
        let body = r.body_mut().read_to_string().map_err(|e| e.to_string())?;
        let v: serde_json::Value = serde_json::from_str(&body).map_err(|e| e.to_string())?;
        let tag = v["tag_name"].as_str().unwrap_or("?").to_string();
        let assets = v["assets"]
            .as_array()
            .map(|a| {
                a.iter()
                    .filter_map(|x| Some((x["name"].as_str()?.to_string(), x["browser_download_url"].as_str()?.to_string())))
                    .collect()
            })
            .unwrap_or_default();
        Ok(Source::Github { repo: repo.to_string(), tag, assets })
    }

    pub fn label(&self) -> String {
        match self {
            Source::Github { repo, tag, .. } => format!("{repo} {tag}"),
            Source::Local(p) => p.display().to_string(),
        }
    }

    /// a release file into `dest`, progress(done, total)
    fn fetch(&self, name: &str, dest: &Path, progress: &mut dyn FnMut(u64, u64)) -> Result<(), String> {
        match self {
            Source::Local(dir) => {
                fs::copy(dir.join(name), dest).map_err(|e| format!("{name}: {e}"))?;
                Ok(())
            }
            Source::Github { assets, tag, .. } => {
                let url = assets.get(name).ok_or(format!("release {tag} has no file {name}"))?;
                let mut r = agent().get(url).call().map_err(|e| format!("{name}: {e}"))?;
                let total: u64 = r
                    .headers()
                    .get("content-length")
                    .and_then(|v| v.to_str().ok())
                    .and_then(|v| v.parse().ok())
                    .unwrap_or(0);
                let mut rd = r.body_mut().with_config().limit(u64::MAX).reader();
                let mut f = fs::File::create(dest).map_err(|e| format!("{}: {e}", dest.display()))?;
                let (mut done, mut buf) = (0u64, vec![0u8; 1 << 16]);
                loop {
                    let n = rd.read(&mut buf).map_err(|e| format!("{name}: {e}"))?;
                    if n == 0 {
                        break;
                    }
                    f.write_all(&buf[..n]).map_err(|e| e.to_string())?;
                    done += n as u64;
                    progress(done, total);
                }
                Ok(())
            }
        }
    }

    pub fn manifest(&self, cache: &Path) -> Result<Manifest, String> {
        fs::create_dir_all(cache).map_err(|e| e.to_string())?;
        let p = cache.join("manifest.json");
        self.fetch("manifest.json", &p, &mut |_, _| {})?;
        let m: Manifest = serde_json::from_slice(&fs::read(&p).map_err(|e| e.to_string())?)
            .map_err(|e| format!("manifest.json: {e}"))?;
        if m.format != 1 || m.title_id != TITLE_ID {
            return Err(format!("unsupported manifest (format {}, title {})", m.format, m.title_id));
        }
        Ok(m)
    }
}

fn sha256_file(p: &Path) -> Result<String, String> {
    let mut h = Sha256::new();
    let mut f = fs::File::open(p).map_err(|e| e.to_string())?;
    let mut buf = vec![0u8; 1 << 16];
    loop {
        let n = f.read(&mut buf).map_err(|e| e.to_string())?;
        if n == 0 {
            break;
        }
        h.update(&buf[..n]);
    }
    Ok(h.finalize().iter().map(|b| format!("{b:02x}")).collect())
}

/// a zip member path that stays inside its folder ("exefs/..." or "romfs/...", no '..', not absolute)
fn safe(zpath: &str) -> bool {
    (zpath.starts_with("exefs/") || zpath.starts_with("romfs/"))
        && Path::new(zpath).components().all(|c| matches!(c, Component::Normal(_)))
}

pub struct Installer<'a> {
    pub target: &'a Target,
    pub source: &'a Source,
    pub manifest: &'a Manifest,
    pub cache: PathBuf,
    pub log: &'a mut dyn FnMut(&str, f32),
}

impl Installer<'_> {
    fn remove(&mut self, files: &[String]) {
        for f in files {
            let p = self.target.dir.join(f);
            let _ = fs::remove_file(&p);
            let mut d = p.parent();                       // prune emptied folders, never above the target dir
            while let Some(dir) = d {
                if dir == self.target.dir || fs::remove_dir(dir).is_err() {
                    break;
                }
                d = dir.parent();
            }
        }
    }

    fn install(&mut self, pkg: &Package, old: Option<&Installed>) -> Result<Installed, String> {
        let zip_path = self.cache.join(&pkg.file);
        let cached = zip_path.exists() && sha256_file(&zip_path).ok().as_deref() == Some(pkg.sha256.as_str());
        if !cached {
            let name = pkg.file.clone();
            let log = &mut *self.log;
            self.source.fetch(&pkg.file, &zip_path, &mut |done, total| {
                let frac = if total > 0 { done as f32 / total as f32 } else { 0.0 };
                log(&format!("downloading {name}: {} / {} MB", done >> 20, total >> 20), frac);
            })?;
            let got = fs::metadata(&zip_path).map(|m| m.len()).unwrap_or(0);
            if got != pkg.size {
                let _ = fs::remove_file(&zip_path);
                return Err(format!("{}: got {got} bytes of {} (download cut short), try again", pkg.file, pkg.size));
            }
            if sha256_file(&zip_path)? != pkg.sha256 {
                let _ = fs::remove_file(&zip_path);
                return Err(format!("{}: checksum mismatch (download damaged), try again", pkg.file));
            }
        }
        if let Some(o) = old {
            self.remove(&o.files);
        }
        (self.log)(&format!("installing {} {}", pkg.name, pkg.version), 1.0);
        let f = fs::File::open(&zip_path).map_err(|e| e.to_string())?;
        let mut z = zip::ZipArchive::new(f).map_err(|e| format!("{}: {e}", pkg.file))?;
        let mut files = Vec::new();
        for i in 0..z.len() {
            let mut e = z.by_index(i).map_err(|e| e.to_string())?;
            if e.is_dir() {
                continue;
            }
            let zpath = e.name().to_string();
            if !safe(&zpath) {
                return Err(format!("{}: refusing path {zpath}", pkg.file));
            }
            let rel = self.target.rel_dest(&self.manifest.mod_name, &zpath);
            let dest = self.target.dir.join(&rel);
            fs::create_dir_all(dest.parent().unwrap()).map_err(|e| format!("{}: {e}", dest.display()))?;
            let mut out = fs::File::create(&dest).map_err(|e| format!("{}: {e}", dest.display()))?;
            std::io::copy(&mut e, &mut out).map_err(|e| format!("{}: {e}", dest.display()))?;
            files.push(rel);
        }
        Ok(Installed { version: pkg.version.clone(), files })
    }

    fn current(&self, inst: Option<&Installed>, pkg: &Package) -> bool {
        inst.is_some_and(|i| i.version == pkg.version && i.files.iter().all(|f| self.target.dir.join(f).exists()))
    }

    /// make the target hold exactly the core + `want` (monster names) of the manifest; empty = uninstall everything
    pub fn apply(&mut self, want: &[String]) -> Result<(), String> {
        let mod_name = self.manifest.mod_name.clone();
        let mut rec = self.target.record(&mod_name);
        for name in want {
            let m = self.manifest.monsters.iter().find(|m| &m.name == name).ok_or(format!("unknown monster {name}"))?;
            if vtuple(&m.requires_core) > vtuple(&self.manifest.core.version) {
                return Err(format!("{} needs core {}, the release has {}", m.title, m.requires_core, self.manifest.core.version));
            }
        }
        let drop: Vec<String> = rec.monsters.keys().filter(|k| !want.contains(k)).cloned().collect();
        for name in drop {
            (self.log)(&format!("removing {name}"), 1.0);
            let files = rec.monsters.remove(&name).unwrap().files;
            self.remove(&files);
            self.target.save_record(&mod_name, &rec)?;
        }
        if want.is_empty() {
            if let Some(c) = rec.core.take() {
                (self.log)("removing the core", 1.0);
                self.remove(&c.files);
            }
            self.target.save_record(&mod_name, &rec)?;
            (self.log)("uninstalled", 1.0);
            return Ok(());
        }
        let core = self.manifest.core.clone();
        if !self.current(rec.core.as_ref(), &core) {
            let inst = self.install(&core, rec.core.as_ref())?;
            rec.core = Some(inst);
            self.target.save_record(&mod_name, &rec)?;
        }
        for name in want {
            let m = self.manifest.monsters.iter().find(|m| &m.name == name).unwrap().clone();
            if !self.current(rec.monsters.get(name), &m) {
                let inst = self.install(&m, rec.monsters.get(name))?;
                rec.monsters.insert(name.clone(), inst);
                self.target.save_record(&mod_name, &rec)?;
            }
        }
        (self.log)("done", 1.0);
        Ok(())
    }
}

/// per-user download cache
pub fn cache_dir() -> PathBuf {
    dirs::cache_dir().unwrap_or_else(std::env::temp_dir).join("mh4uport-installer")
}
