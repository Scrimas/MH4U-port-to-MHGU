//! Where releases come from: GitHub releases, or a local folder (tests, offline use: a `releases.json` in the GitHub
//! API's shape whose download URLs are paths relative to it). The mod's releases (`v2.0.0`, `v2.1.0-pre.1`) are on
//! PACKAGES_REPO (or `MHGU_DE_RELEASES=<folder>`), the installer's (`v2.0.0`, with its .exe and AppImage) on REPO (or
//! `MHGU_DE_INSTALLER_RELEASES=<folder>`), whose older `v1.x` releases are the mod's from before the split. One list
//! call per repository and start (GitHub allows 60 unauthenticated API calls an hour per address; asset downloads do
//! not count).

use crate::i18n::{tr, trf};
use crate::version::Version;
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;

#[derive(Clone, Debug, Deserialize)]
pub struct Asset {
    pub name: String,
    #[serde(rename = "browser_download_url")]
    pub url: String,
    pub size: u64,
}

#[derive(Clone, Debug, Deserialize)]
pub struct Release {
    #[serde(rename = "tag_name")]
    pub tag: String,
    #[serde(default, rename = "html_url")]
    pub page: String,
    #[serde(default, rename = "published_at")]
    pub date: String,
    #[serde(default)]
    pub draft: bool,
    #[serde(default)]
    pub prerelease: bool,
    #[serde(default)]
    pub assets: Vec<Asset>,
}

impl Release {
    pub fn asset(&self, name: &str) -> Option<&Asset> {
        self.assets.iter().find(|a| a.name == name)
    }

    pub fn version(&self) -> Option<Version> {
        Version::parse(&self.tag)
    }

    /// Published, "2026-11-09" (UTC); empty when unknown.
    pub fn day(&self) -> &str {
        self.date.get(..10).unwrap_or_default()
    }
}

#[derive(Clone, Debug)]
pub enum Source {
    GitHub(String),
    Local(PathBuf),
}

/// The mod's releases this installer can install, newest first: tag `v<version>` from FIRST_RELEASE on, with a
/// manifest; pre-releases only when asked.
pub fn mod_releases(all: &[Release], prereleases: bool) -> Vec<Release> {
    let first = Version::parse(crate::FIRST_RELEASE);
    let mut v: Vec<Release> = all
        .iter()
        .filter(|r| r.tag.starts_with('v') && !r.draft && (prereleases || !r.prerelease))
        .filter(|r| r.version().is_some() && r.version() >= first && r.asset("manifest.json").is_some())
        .cloned()
        .collect();
    v.sort_by_key(|r| std::cmp::Reverse(r.version()));
    v
}

/// The file name every installer build starts with (installer/packaging/build.py NAME).
pub const INSTALLER_ASSET: &str = "MHGU-Definitive-Edition-Installer-";

/// The installer's own releases, newest first: tag `v<version>` with an installer file (REPO's v1.x releases are the
/// mod's, from before the split); its pre-releases are left out.
pub fn installer_releases(all: &[Release]) -> Vec<Release> {
    let mut v: Vec<Release> = all
        .iter()
        .filter(|r| r.tag.starts_with('v') && !r.draft && !r.prerelease && r.version().is_some())
        .filter(|r| r.assets.iter().any(|a| a.name.starts_with(INSTALLER_ASSET)))
        .cloned()
        .collect();
    v.sort_by_key(|r| std::cmp::Reverse(r.version()));
    v
}

fn agent() -> ureq::Agent {
    ureq::Agent::config_builder()
        .https_only(true)
        .timeout_connect(Some(Duration::from_secs(15)))
        .timeout_recv_response(Some(Duration::from_secs(30)))
        // a stalled download fails instead of waiting forever (Cancel also leaves)
        .timeout_recv_body(Some(Duration::from_secs(30 * 60)))
        .user_agent(format!("mhgu-de-installer/{}", crate::VERSION))
        .build()
        .into()
}

fn http(url: &str) -> Result<Box<dyn Read + Send>, String> {
    let req = agent().get(url).header("Accept", "application/vnd.github+json");
    match req.call() {
        Ok(r) => Ok(Box::new(r.into_body().into_reader())),
        Err(ureq::Error::StatusCode(403 | 429)) => {
            Err(tr("GitHub refused the request (too many in the last hour), try later"))
        }
        Err(ureq::Error::StatusCode(c)) => Err(trf("GitHub answered HTTP {}", &[&c])),
        Err(e) => Err(trf("Could not reach GitHub ({})", &[&e])),
    }
}

impl Source {
    /// The mod's releases: `MHGU_DE_RELEASES=<folder>` when set (tests), else PACKAGES_REPO.
    pub fn mods() -> Source {
        Source::from_env("MHGU_DE_RELEASES", crate::PACKAGES_REPO)
    }

    /// The installer's releases: `MHGU_DE_INSTALLER_RELEASES=<folder>` when set (tests), else REPO.
    pub fn installer() -> Source {
        Source::from_env("MHGU_DE_INSTALLER_RELEASES", crate::REPO)
    }

    fn from_env(var: &str, repo: &str) -> Source {
        match std::env::var_os(var).filter(|v| !v.is_empty()) {
            Some(d) => Source::Local(PathBuf::from(d)),
            None => Source::GitHub(repo.to_string()),
        }
    }

    fn open(&self, url: &str) -> Result<Box<dyn Read + Send>, String> {
        match self {
            Source::GitHub(_) => http(url),
            Source::Local(dir) => {
                let p = dir.join(url);
                std::fs::File::open(&p)
                    .map(|f| Box::new(f) as Box<dyn Read + Send>)
                    .map_err(|e| trf("Could not read {} ({})", &[&p.display(), &e]))
            }
        }
    }

    /// Every release (drafts left out by GitHub for anyone but the owner, and here too).
    pub fn releases(&self) -> Result<Vec<Release>, String> {
        let url = match self {
            Source::GitHub(repo) => format!("https://api.github.com/repos/{repo}/releases?per_page=100"),
            Source::Local(_) => "releases.json".to_string(),
        };
        let all: Vec<Release> =
            serde_json::from_reader(self.open(&url)?).map_err(|e| trf("Unexpected answer from GitHub ({})", &[&e]))?;
        Ok(all.into_iter().filter(|r| !r.draft).collect())
    }

    /// A small asset (manifest, icons, checksums), whole.
    pub fn bytes(&self, a: &Asset) -> Result<Vec<u8>, String> {
        let mut out = Vec::with_capacity(a.size as usize);
        self.open(&a.url)?
            .take(a.size.max(1) * 2 + 1024)
            .read_to_end(&mut out)
            .map_err(|e| trf("Download failed ({})", &[&e]))?;
        Ok(out)
    }

    /// Download `a` into `to` (through `<to>.part`), with `progress(done, total)`; returns its sha256 (hex).
    pub fn download(
        &self,
        a: &Asset,
        to: &Path,
        progress: &dyn Fn(u64, u64),
        cancel: &AtomicBool,
    ) -> Result<String, String> {
        let part =
            to.with_file_name(format!("{}.part", to.file_name().map(|n| n.to_string_lossy()).unwrap_or_default()));
        let err = |e: std::io::Error| trf("Could not write {} ({})", &[&part.display(), &e]);
        if let Some(d) = to.parent() {
            std::fs::create_dir_all(d).map_err(err)?;
        }
        let res = (|| {
            let mut body = self.open(&a.url)?;
            let mut out = std::fs::File::create(&part).map_err(err)?;
            let mut hash = Sha256::new();
            let mut buf = vec![0; 64 * 1024];
            let mut done = 0;
            loop {
                if cancel.load(Ordering::Relaxed) {
                    return Err(tr("Cancelled"));
                }
                let n = body.read(&mut buf).map_err(|e| trf("Download failed ({})", &[&e]))?;
                if n == 0 {
                    break;
                }
                hash.update(&buf[..n]);
                out.write_all(&buf[..n]).map_err(err)?;
                done += n as u64;
                progress(done, a.size);
            }
            out.sync_all().map_err(err)?;
            drop(out);
            std::fs::rename(&part, to).map_err(err)?;
            Ok(hex(&hash.finalize()))
        })();
        if res.is_err() {
            let _ = std::fs::remove_file(&part);
        }
        res
    }
}

pub fn hex(b: &[u8]) -> String {
    b.iter().map(|x| format!("{x:02x}")).collect()
}

pub fn sha256_file(p: &Path) -> std::io::Result<String> {
    let mut f = std::fs::File::open(p)?;
    let mut h = Sha256::new();
    let mut buf = vec![0; 256 * 1024];
    loop {
        let n = f.read(&mut buf)?;
        if n == 0 {
            break;
        }
        h.update(&buf[..n]);
    }
    Ok(hex(&h.finalize()))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rel(tag: &str, pre: bool, assets: &[&str]) -> Release {
        Release {
            tag: tag.into(),
            page: String::new(),
            date: "2026-11-09T10:00:00Z".into(),
            draft: false,
            prerelease: pre,
            assets: assets.iter().map(|n| Asset { name: n.to_string(), url: n.to_string(), size: 1 }).collect(),
        }
    }

    #[test]
    fn mod_releases_need_a_manifest() {
        let packages = [
            rel("v2.0.0", false, &["manifest.json", "core-2.0.0.zip"]),
            rel("v2.1.0-pre.1", true, &["manifest.json"]),
            rel("v1.10.0", false, &["manifest.json"]),
        ];
        let tags = |v: Vec<Release>| v.into_iter().map(|r| r.tag).collect::<Vec<_>>();
        assert_eq!(tags(mod_releases(&packages, false)), ["v2.0.0"], "1.10.0 is older than the first release");
        assert_eq!(tags(mod_releases(&packages, true)), ["v2.1.0-pre.1", "v2.0.0"]);
        assert_eq!(packages[0].day(), "2026-11-09");
    }

    #[test]
    fn installer_releases_are_those_with_an_installer() {
        let repo = [
            rel("v2.1.0", false, &["MHGU-Definitive-Edition-Installer-2.1.0-x86_64.exe", "SHA256SUMS-2.1.0"]),
            rel("v2.2.0-pre.1", true, &["MHGU-Definitive-Edition-Installer-2.2.0-pre.1-x86_64.exe"]),
            rel("v1.9.0", false, &["core-1.9.0.zip", "gogmazios-1.1.7.zip"]),
            rel("v2.0.0", false, &["MHGU-Definitive-Edition-Installer-2.0.0-x86_64.AppImage"]),
        ];
        let tags = |v: Vec<Release>| v.into_iter().map(|r| r.tag).collect::<Vec<_>>();
        assert_eq!(tags(installer_releases(&repo)), ["v2.1.0", "v2.0.0"], "the mod's v1.x and pre-releases left out");
    }

    #[test]
    fn a_local_folder_serves_releases_and_downloads() {
        let d = std::env::temp_dir().join(format!("mhgu-de-source-{}", std::process::id()));
        std::fs::create_dir_all(d.join("v1.10.0")).unwrap();
        std::fs::write(d.join("v1.10.0/core-1.10.0.zip"), b"zipdata").unwrap();
        std::fs::write(
            d.join("releases.json"),
            r#"[{"tag_name":"v1.10.0","assets":[{"name":"core-1.10.0.zip","browser_download_url":"v1.10.0/core-1.10.0.zip","size":7}]}]"#,
        )
        .unwrap();
        let s = Source::Local(d.clone());
        let r = s.releases().unwrap();
        let a = r[0].asset("core-1.10.0.zip").unwrap();
        assert_eq!(s.bytes(a).unwrap(), b"zipdata");
        let to = d.join("cache/core-1.10.0.zip");
        let sum = s.download(a, &to, &|_, _| {}, &AtomicBool::new(false)).unwrap();
        assert_eq!(sum, sha256_file(&to).unwrap());
        assert!(s.download(a, &to, &|_, _| {}, &AtomicBool::new(true)).is_err(), "cancelled");
        std::fs::remove_dir_all(&d).unwrap();
    }
}
