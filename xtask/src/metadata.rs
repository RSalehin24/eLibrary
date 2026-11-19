use std::process::Command;

use serde::Deserialize;

use crate::boundaries::Edges;

#[derive(Deserialize)]
struct Metadata {
    packages: Vec<Package>,
}

#[derive(Deserialize)]
struct Package {
    name: String,
    dependencies: Vec<Dependency>,
}

#[derive(Deserialize)]
struct Dependency {
    name: String,
    path: Option<String>,
}

/// Workspace crate edges from `cargo metadata` (path dependencies only).
///
/// # Errors
/// Returns a message when cargo cannot run or its output is not understood.
pub fn workspace_edges() -> Result<Edges, String> {
    let output = Command::new("cargo")
        .args(["metadata", "--format-version", "1", "--no-deps"])
        .output()
        .map_err(|error| format!("cannot run cargo metadata: {error}"))?;
    let metadata: Metadata = serde_json::from_slice(&output.stdout)
        .map_err(|error| format!("cannot read cargo metadata: {error}"))?;
    Ok(metadata
        .packages
        .into_iter()
        .map(|package| (package.name, workspace_dependencies(package.dependencies)))
        .collect())
}

fn workspace_dependencies(dependencies: Vec<Dependency>) -> Vec<String> {
    dependencies
        .into_iter()
        .filter(|dependency| dependency.path.is_some())
        .map(|dependency| dependency.name)
        .collect()
}
