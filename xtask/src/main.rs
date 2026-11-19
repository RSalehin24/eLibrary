//! Workspace tooling. `cargo xtask check` runs the local gates; `cargo xtask boundaries` only Q6.

mod boundaries;
mod codegen;
mod gates;
mod metadata;

use std::io::Write;
use std::process::ExitCode;

fn main() -> ExitCode {
    let mut out = std::io::stdout();
    match std::env::args().nth(1).as_deref() {
        Some("check") => finish(&gates::run_all(&mut out), &mut out),
        Some("boundaries") => boundaries_only(&mut out),
        Some("codegen") => codegen_command(&mut out),
        _ => {
            let _ = writeln!(
                out,
                "usage: cargo xtask <check|boundaries|codegen [--check]>"
            );
            ExitCode::from(2)
        }
    }
}

fn codegen_command(out: &mut impl Write) -> ExitCode {
    let mode = if std::env::args().nth(2).as_deref() == Some("--check") {
        codegen::Mode::Check
    } else {
        codegen::Mode::Write
    };
    match codegen::run(std::path::Path::new("."), mode) {
        Ok(stale) => report_codegen(&stale, mode, out),
        Err(message) => {
            let _ = writeln!(out, "{message}");
            ExitCode::FAILURE
        }
    }
}

fn report_codegen(
    stale: &[std::path::PathBuf],
    mode: codegen::Mode,
    out: &mut impl Write,
) -> ExitCode {
    let verb = match mode {
        codegen::Mode::Check => "out of date",
        codegen::Mode::Write => "written",
    };
    for path in stale {
        let _ = writeln!(out, "{}: {verb}", path.display());
    }
    if mode == codegen::Mode::Check && !stale.is_empty() {
        return ExitCode::FAILURE;
    }
    ExitCode::SUCCESS
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
