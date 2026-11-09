//! The installer's settings: `<config>/mh4uport-installer/settings.json` (Linux ~/.config, Windows %APPDATA%), and
//! its download cache `<cache>/mh4uport-installer/<release>/` (Linux ~/.cache, Windows %LOCALAPPDATA%): only the
//! installed release's zips stay (apply.rs prune_cache after each install).

use crate::places::Custom;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default)]
pub struct Settings {
    /// Offer the mod's pre-releases (the player accepted the warning).
    pub prereleases: bool,
    /// Look for a newer installer at start.
    pub check_updates: bool,
    /// "" = the system's language, else a catalog code (fr, de, es, it, zh_TW, zh_CN, en).
    pub language: String,
    /// The ticked places (Place::id).
    pub ticked: Vec<String>,
    /// Places added by the player.
    pub custom: Vec<Custom>,
    /// The online warning was shown once.
    pub warned_online: bool,
    /// Windows: the old .exe an update left aside, deleted at the next start.
    pub update_leftover: Option<PathBuf>,
}

impl Default for Settings {
    fn default() -> Self {
        Settings {
            prereleases: false,
            check_updates: true,
            language: String::new(),
            ticked: vec![],
            custom: vec![],
            warned_online: false,
            update_leftover: None,
        }
    }
}

pub fn dir() -> PathBuf {
    if let Some(d) = std::env::var_os("MH4UPORT_CONFIG").filter(|v| !v.is_empty()) {
        return PathBuf::from(d);
    }
    dirs::config_dir().unwrap_or_else(std::env::temp_dir).join("mh4uport-installer")
}

pub fn cache_dir() -> PathBuf {
    if let Some(d) = std::env::var_os("MH4UPORT_CACHE").filter(|v| !v.is_empty()) {
        return PathBuf::from(d);
    }
    dirs::cache_dir().unwrap_or_else(std::env::temp_dir).join("mh4uport-installer")
}

pub fn load() -> Settings {
    std::fs::read(dir().join("settings.json")).ok().and_then(|b| serde_json::from_slice(&b).ok()).unwrap_or_default()
}

pub fn save(s: &Settings) -> std::io::Result<()> {
    let d = dir();
    std::fs::create_dir_all(&d)?;
    let tmp = d.join("settings.json.tmp");
    std::fs::write(&tmp, serde_json::to_string_pretty(s).expect("settings serialise"))?;
    std::fs::rename(tmp, d.join("settings.json"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn missing_fields_take_their_default() {
        let s: Settings = serde_json::from_str(r#"{"prereleases": true}"#).unwrap();
        assert!(s.prereleases && s.check_updates && s.ticked.is_empty());
    }
}
