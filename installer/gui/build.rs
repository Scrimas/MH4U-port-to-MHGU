//! The window (ui/app.slint, Fluent style: it follows the system's light / dark) with its translations bundled from
//! lang/ (installer/tools/i18n.py keeps them in step; src/i18n.rs reads the same catalogs for the Rust strings), and
//! on Windows the icon and the DPI-aware manifest.

fn main() {
    let config = slint_build::CompilerConfiguration::new()
        .with_bundled_translations("lang")
        .with_default_translation_context(slint_build::DefaultTranslationContext::None)
        .with_style("fluent".into());
    slint_build::compile_with_config("ui/app.slint", config).unwrap();
    println!("cargo:rerun-if-changed=lang");
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("windows") {
        let mut res = winresource::WindowsResource::new();
        res.set_manifest(include_str!("windows/app.manifest"));
        res.set_icon("assets/icon.ico");
        res.compile().unwrap();
    }
}
