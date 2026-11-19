//! `cargo xtask check`: the PR gates that can run locally (Q1, Q2, Q6, Q7).

use std::process::Command;

use crate::{boundaries, containers, metadata, register};

struct Step {
    name: &'static str,
    program: &'static str,
    arguments: &'static [&'static str],
}

const COMMAND_STEPS: [Step; 12] = [
    Step {
        name: "Q1 fmt",
        program: "cargo",
        arguments: &["fmt", "--check"],
    },
    Step {
        name: "Q1 clippy",
        program: "cargo",
        arguments: &["clippy", "--all-targets", "--", "-D", "warnings"],
    },
    Step {
        name: "Q2 tests",
        program: "cargo",
        arguments: &["test", "--quiet"],
    },
    Step {
        name: "Q3 contracts",
        program: "cargo",
        arguments: &["xtask", "codegen", "--check"],
    },
    Step {
        name: "Q5 deny",
        program: "cargo",
        arguments: &["deny", "check"],
    },
    Step {
        name: "Q5 audit",
        program: "cargo",
        arguments: &["audit"],
    },
    Step {
        name: "Q8 models",
        program: "bash",
        arguments: &["deploy/scripts/check-models.sh"],
    },
    Step {
        name: "Q1 web lint",
        program: "npm",
        arguments: &["--prefix", "web", "run", "lint"],
    },
    Step {
        name: "Q2 web build",
        program: "npm",
        arguments: &["--prefix", "web", "run", "build"],
    },
    Step {
        name: "Q2 web tests",
        program: "npm",
        arguments: &["--prefix", "web", "test", "--", "--no-watch"],
    },
    Step {
        name: "Q2 web e2e and accessibility",
        program: "npm",
        arguments: &["--prefix", "web", "run", "e2e"],
    },
    Step {
        name: "Q7 plan check",
        program: "python3",
        arguments: &["planning/tools/check_plan.py"],
    },
];

/// Runs every gate and returns the names of the ones that failed.
#[must_use]
pub fn run_all(report: &mut impl std::io::Write) -> Vec<&'static str> {
    let mut failed: Vec<&'static str> = COMMAND_STEPS
        .iter()
        .filter(|step| !run_step(step, report))
        .map(|step| step.name)
        .collect();
    if !boundaries_clean(report) {
        failed.push("Q6 dependency boundaries");
    }
    if !register_clean(report) {
        failed.push("Q10 dependency register");
    }
    if !containers_clean(report) {
        failed.push("Q11 containers");
    }
    failed
}

fn run_step(step: &Step, report: &mut impl std::io::Write) -> bool {
    let output = Command::new(step.program)
        .args(step.arguments)
        .env("PATH", path_with_cargo_bin())
        .output();
    let passed = output.as_ref().is_ok_and(|output| output.status.success());
    let _ = writeln!(
        report,
        "{} {}",
        if passed { "ok  " } else { "FAIL" },
        step.name
    );
    if let (false, Ok(output)) = (passed, output) {
        let _ = report.write_all(&output.stdout);
        let _ = report.write_all(&output.stderr);
    }
    passed
}

fn boundaries_clean(report: &mut impl std::io::Write) -> bool {
    let found = metadata::workspace_edges().map(|edges| boundaries::violations(&edges));
    match found {
        Ok(lines) if lines.is_empty() => {
            let _ = writeln!(report, "ok   Q6 dependency boundaries");
            true
        }
        Ok(lines) => {
            let _ = writeln!(
                report,
                "FAIL Q6 dependency boundaries\n  {}",
                lines.join("\n  ")
            );
            false
        }
        Err(message) => {
            let _ = writeln!(report, "FAIL Q6 dependency boundaries: {message}");
            false
        }
    }
}

// why: `cargo install` puts cargo-deny and cargo-audit in ~/.cargo/bin, often missing from PATH.
fn path_with_cargo_bin() -> std::ffi::OsString {
    let mut paths: Vec<std::path::PathBuf> =
        std::env::var_os("PATH").map_or_default(|path| std::env::split_paths(&path).collect());
    if let Some(home) = std::env::var_os("HOME") {
        paths.push(std::path::PathBuf::from(home).join(".cargo").join("bin"));
    }
    std::env::join_paths(paths).unwrap_or_default()
}

const REGISTER_PATH: &str = "planning/04-architecture/dependency-policy.md";

fn register_clean(report: &mut impl std::io::Write) -> bool {
    let missing = std::fs::read_to_string(REGISTER_PATH)
        .map_err(|error| format!("cannot read {REGISTER_PATH}: {error}"))
        .and_then(|text| {
            metadata::external_dependencies().map(|names| register::unapproved(&text, &names))
        });
    report_lines(
        report,
        "Q10 dependency register",
        missing.map(|names| {
            names
                .iter()
                .map(|n| format!("{n} has no APPROVED register entry"))
                .collect()
        }),
    )
}

fn containers_clean(report: &mut impl std::io::Write) -> bool {
    let lines = compose_config().map(|config| containers::violations(&config));
    report_lines(report, "Q11 containers", lines)
}

fn compose_config() -> Result<serde_json::Value, String> {
    let output = Command::new("docker")
        .args([
            "compose",
            "--profile",
            "backup",
            "-f",
            "deploy/compose/compose.yaml",
            "config",
            "--format",
            "json",
        ])
        .output()
        .map_err(|error| format!("cannot run docker compose: {error}"))?;
    serde_json::from_slice(&output.stdout)
        .map_err(|error| format!("cannot read compose config: {error}"))
}

fn report_lines(
    report: &mut impl std::io::Write,
    name: &str,
    lines: Result<Vec<String>, String>,
) -> bool {
    match lines {
        Ok(found) if found.is_empty() => {
            let _ = writeln!(report, "ok   {name}");
            true
        }
        Ok(found) => {
            let _ = writeln!(report, "FAIL {name}\n  {}", found.join("\n  "));
            false
        }
        Err(message) => {
            let _ = writeln!(report, "FAIL {name}: {message}");
            false
        }
    }
}
