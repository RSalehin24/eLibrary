//! Workspace tooling. `cargo xtask check` runs the local gates; `cargo xtask boundaries` only Q6.

mod boundaries;
mod gates;
mod metadata;

use std::io::Write;
use std::process::ExitCode;

fn main() -> ExitCode {
    let mut out = std::io::stdout();
    match std::env::args().nth(1).as_deref() {
        Some("check") => finish(&gates::run_all(&mut out), &mut out),
        Some("boundaries") => boundaries_only(&mut out),
        _ => {
            let _ = writeln!(out, "usage: cargo xtask <check|boundaries>");
            ExitCode::from(2)
        }
    }
}

fn boundaries_only(out: &mut impl Write) -> ExitCode {
    match metadata::workspace_edges().map(|edges| boundaries::violations(&edges)) {
        Ok(lines) if lines.is_empty() => ExitCode::SUCCESS,
        Ok(lines) => {
            let _ = writeln!(out, "{}", lines.join("\n"));
            ExitCode::FAILURE
        }
        Err(message) => {
            let _ = writeln!(out, "{message}");
            ExitCode::FAILURE
        }
    }
}

fn finish(failed: &[&str], out: &mut impl Write) -> ExitCode {
    if failed.is_empty() {
        return ExitCode::SUCCESS;
    }
    let _ = writeln!(out, "failed: {}", failed.join(", "));
    ExitCode::FAILURE
}
