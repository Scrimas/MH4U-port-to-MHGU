//! Where releases come from: the repository's GitHub releases, or a local folder (tests, offline use:
//! `MH4UPORT_RELEASES=<folder>`, a `releases.json` in the GitHub API's shape whose download URLs are paths relative
//! to it). The mod's releases (`v1.10.0`, `v1.11.0-pre.1`) and the installer's (`installer-v1.0.0`) share the
//! repository: one list call per start serves both (GitHub allows 60 unauthenticated API calls an hour per address;
//! asset downloads do not count).

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

/// The installer's own releases, newest first (`installer-v*`; its pre-releases are left out).
pub fn installer_releases(all: &[Release]) -> Vec<Release> {
    let mut v: Vec<Release> = all
        .iter()
        .filter(|r| r.tag.starts_with("installer-v") && !r.draft && !r.prerelease && r.version().is_some())
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
        .user_agent(format!("mh4uport-installer/{}", crate::VERSION))
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
    /// `MH4UPORT_RELEASES=<folder>` when set (tests), else GitHub.
    pub fn from_env() -> Source {
        match std::env::var_os("MH4UPORT_RELEASES").filter(|v| !v.is_empty()) {
            Some(d) => Source::Local(PathBuf::from(d)),
            None => Source::GitHub(crate::REPO.to_string()),
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
    fn mod_and_installer_releases_are_told_apart() {
        let all = [
            rel("installer-v1.1.0", false, &["MH4U-Port-Installer-1.1.0-x86_64.exe"]),
            rel("v1.9.0", false, &["core-1.9.0.zip"]),
            rel("v1.10.0", false, &["manifest.json"]),
            rel("v1.11.0-pre.1", true, &["manifest.json"]),
            rel("installer-v1.2.0-pre.1", true, &[]),
        ];
        let tags = |v: Vec<Release>| v.into_iter().map(|r| r.tag).collect::<Vec<_>>();
        assert_eq!(tags(mod_releases(&all, false)), ["v1.10.0"], "1.9.0 has no manifest");
        assert_eq!(tags(mod_releases(&all, true)), ["v1.11.0-pre.1", "v1.10.0"]);
        assert_eq!(tags(installer_releases(&all)), ["installer-v1.1.0"]);
        assert_eq!(all[2].day(), "2026-11-09");
    }

    #[test]
    fn a_local_folder_serves_releases_and_downloads() {
        let d = std::env::temp_dir().join(format!("mh4u-source-{}", std::process::id()));
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
