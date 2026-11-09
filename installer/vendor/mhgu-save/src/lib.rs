//! Vendored from MHGU_Editor app/core (crate mhgu-save) by installer/tools/vendor_save.py: do not edit,
//! refresh with that script (installer/vendor/VENDORED.toml names the commit).

pub mod equipment;
pub mod items;
pub mod save;
pub mod store;

pub use save::{Error, Save};
