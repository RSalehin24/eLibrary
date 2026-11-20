use std::io::Read;
use std::net::TcpStream;
use std::process::{Child, Command, Stdio};
use std::time::{Duration, Instant};

const STARTUP_LIMIT: Duration = Duration::from_secs(10);
const STOP_LIMIT: Duration = Duration::from_secs(3);

fn key_file() -> std::io::Result<String> {
    let path = format!("{}/shutdown-test-key", env!("CARGO_TARGET_TMPDIR"));
    std::fs::write(&path, "cd".repeat(32))?;
    Ok(path)
}

fn start(port: u16) -> std::io::Result<Child> {
    let key = key_file()?;
    Command::new(env!("CARGO_BIN_EXE_svc-gateway"))
        .env("ELIBRARY_PUBLIC_ORIGIN", "https://library.test")
        .env("ELIBRARY_UPSTREAM_IDENTITY", "http://127.0.0.1:1")
        .env("ELIBRARY_UPSTREAM_CATALOG", "http://127.0.0.1:1")
        .env("ELIBRARY_UPSTREAM_READER", "http://127.0.0.1:1")
        .env("ELIBRARY_UPSTREAM_INGESTION", "http://127.0.0.1:1")
        .env("ELIBRARY_SERVICE_TOKEN_KEY_FILE", key)
        .env("ELIBRARY_LISTEN_ADDRESS", format!("127.0.0.1:{port}"))
        .env(
            "ELIBRARY_INTERNAL_ADDRESS",
            format!("127.0.0.1:{}", port + 1),
        )
        .stdout(Stdio::piped())
        .spawn()
}

fn wait_until_listening(port: u16) -> bool {
    let deadline = Instant::now() + STARTUP_LIMIT;
    std::iter::from_fn(|| (Instant::now() < deadline).then_some(()))
        .any(|()| listening_after_pause(port))
}

fn listening_after_pause(port: u16) -> bool {
    if TcpStream::connect(("127.0.0.1", port)).is_ok() {
        return true;
    }
    std::thread::sleep(Duration::from_millis(50));
    false
}

#[test]
fn sigterm_stops_the_service_promptly_with_success() -> Result<(), Box<dyn std::error::Error>> {
    let port = 20_000 + u16::try_from(std::process::id() % 20_000)?;
    let mut child = start(port)?;
    assert!(
        wait_until_listening(port + 1),
        "service never started listening"
    );
    Command::new("kill")
        .arg("-TERM")
        .arg(child.id().to_string())
        .status()?;
    let stopped_at = Instant::now();
    let status = child.wait()?;
    assert!(status.success(), "exit status {status}");
    assert!(
        stopped_at.elapsed() < STOP_LIMIT,
        "took {:?}",
        stopped_at.elapsed()
    );
    let mut logs = String::new();
    if let Some(mut stdout) = child.stdout.take() {
        stdout.read_to_string(&mut logs)?;
    }
    assert!(logs.contains("stopped"), "logs: {logs}");
    Ok(())
}
