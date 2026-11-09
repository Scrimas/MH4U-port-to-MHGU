//! MH4U Port Installer without its window: the GitHub releases of the mod (`manifest.json` + zips made by
//! tools/release.py), the install places (emulators, SD cards, folders), the install record kept in each place, the
//! planner (what one set of monsters means for every ticked place), the install itself (download, check, extract,
//! swap) and the installer's own update. The window (installer/gui) and the command line (src/bin/cli.rs) both drive
//! it; nothing here waits on a UI.

pub mod apply;
pub mod i18n;
pub mod manifest;
pub mod places;
pub mod plan;
pub mod record;
pub mod saves;
pub mod selfupdate;
pub mod settings;
pub mod source;
pub mod version;
pub mod zipread;

/// This installer's version (the workspace's).
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
/// The repository of the mod and of the installer's own releases (public).
pub const REPO: &str = "Scrimas/MH4U-port-to-MHGU";
/// The first mod release with a manifest: older ones cannot be installed by this app.
pub const FIRST_RELEASE: &str = "1.10.0";
