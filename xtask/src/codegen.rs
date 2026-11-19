//! Gate Q3: generated contract documents are committed; CI regenerates and fails on any diff.

use std::path::{Path, PathBuf};

use contracts_http::CommonApi;
use utoipa::OpenApi;

/// How `codegen` treats the committed files.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    Write,
    Check,
}

struct Generated {
    path: PathBuf,
    contents: String,
}

/// Returns the paths that are out of date (in `Check` mode) or were rewritten (in `Write` mode).
///
/// # Errors
/// Returns a message when a document cannot be rendered or a file cannot be read or written.
pub fn run(root: &Path, mode: Mode) -> Result<Vec<PathBuf>, String> {
    let mut stale = Vec::new();
    for document in documents(root)?
        .into_iter()
        .filter(|document| !is_current(document))
    {
        apply(&document, mode)?;
        stale.push(document.path);
    }
    Ok(stale)
}

fn apply(document: &Generated, mode: Mode) -> Result<(), String> {
    match mode {
        Mode::Write => write(document),
        Mode::Check => Ok(()),
    }
}

fn is_current(document: &Generated) -> bool {
    std::fs::read_to_string(&document.path).is_ok_and(|existing| existing == document.contents)
}

fn write(document: &Generated) -> Result<(), String> {
    std::fs::write(&document.path, &document.contents)
        .map_err(|error| format!("cannot write {}: {error}", document.path.display()))
}

fn documents(root: &Path) -> Result<Vec<Generated>, String> {
    let directory = root.join("planning/07-contracts/http/openapi");
    let common = CommonApi::openapi()
        .to_pretty_json()
        .map_err(|error| format!("cannot render common OpenAPI: {error}"))?;
    Ok(vec![Generated {
        path: directory.join("common.json"),
        contents: format!("{common}\n"),
    }])
}

#[cfg(test)]
mod tests {
    use super::*;

    fn scratch_root() -> Result<PathBuf, String> {
        let root = std::env::temp_dir().join(format!("xtask-codegen-{}", std::process::id()));
        std::fs::create_dir_all(root.join("planning/07-contracts/http/openapi"))
            .map_err(|error| error.to_string())?;
        Ok(root)
    }

    #[test]
    fn write_then_check_is_clean_and_drift_is_detected() -> Result<(), String> {
        let root = scratch_root()?;
        assert_eq!(
            run(&root, Mode::Check)?.len(),
            1,
            "missing file counts as stale"
        );
        assert_eq!(run(&root, Mode::Write)?.len(), 1);
        assert_eq!(run(&root, Mode::Check)?, Vec::<PathBuf>::new());
        let file = root.join("planning/07-contracts/http/openapi/common.json");
        std::fs::write(&file, "{}").map_err(|error| error.to_string())?;
        assert_eq!(run(&root, Mode::Check)?.len(), 1, "edited file is stale");
        std::fs::remove_dir_all(&root).map_err(|error| error.to_string())
    }
}
