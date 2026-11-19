//! `cargo xtask check`: the PR gates that can run locally (Q1, Q2, Q6, Q7).

use std::process::Command;

use crate::{boundaries, metadata};

struct Step {
    name: &'static str,
    program: &'static str,
    arguments: &'static [&'static str],
}

const COMMAND_STEPS: [Step; 4] = [
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
    failed
}

fn run_step(step: &Step, report: &mut impl std::io::Write) -> bool {
    let output = Command::new(step.program).args(step.arguments).output();
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
