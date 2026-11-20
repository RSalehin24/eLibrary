//! SMTP settings parsing and the SMTP transport against a tiny in-process fake server.

use std::error::Error;
use std::io::{BufRead, BufReader, Write};
use std::net::{TcpListener, TcpStream};
use std::sync::mpsc::{Receiver, Sender, channel};
use std::thread::JoinHandle;

use platform_config::{ConfigError, MapSource};
use svc_notify::smtp::{Security, SmtpSettings, SmtpTransport};
use svc_notify::transport::{MailTransport, OutgoingMail, SendError};

type TestResult = Result<(), Box<dyn Error>>;

fn base() -> MapSource {
    MapSource::default()
        .with("ELIBRARY_SMTP_HOST", "smtp.example.org")
        .with("ELIBRARY_SMTP_FROM", "ELibrary <noreply@example.org>")
}

#[test]
fn defaults_are_starttls_on_587_without_credentials() -> TestResult {
    let settings = SmtpSettings::from_source(&base())?;
    assert_eq!(settings.port, 587);
    assert_eq!(settings.security, Security::StartTls);
    assert!(settings.credentials.is_none());
    assert_eq!(settings.host, "smtp.example.org");
    Ok(())
}

#[test]
fn bad_settings_are_refused() {
    let cases = [
        base().with("ELIBRARY_SMTP_PORT", "notaport"),
        base().with("ELIBRARY_SMTP_PORT", "70000"),
        base().with("ELIBRARY_SMTP_PORT", "0"),
        base().with("ELIBRARY_SMTP_SECURITY", "none"),
        base().with("ELIBRARY_SMTP_SECURITY", "plain"),
        MapSource::default().with("ELIBRARY_SMTP_FROM", "a@b.c"),
        MapSource::default().with("ELIBRARY_SMTP_HOST", "h.example.org"),
        base().with("ELIBRARY_SMTP_USER", "u"),
    ];
    for source in &cases {
        assert!(SmtpSettings::from_source(source).is_err());
    }
}

#[test]
fn plain_is_accepted_only_for_local_hosts() -> TestResult {
    for host in ["localhost", "127.0.0.1", "mailpit", "relay.internal"] {
        let source = base()
            .with("ELIBRARY_SMTP_HOST", host)
            .with("ELIBRARY_SMTP_SECURITY", "plain");
        assert_eq!(
            SmtpSettings::from_source(&source)?.security,
            Security::Plain
        );
    }
    let public = base().with("ELIBRARY_SMTP_SECURITY", "PLAIN");
    assert!(matches!(
        SmtpSettings::from_source(&public),
        Err(ConfigError::InvalidValue { .. })
    ));
    Ok(())
}

#[test]
fn security_and_port_are_parsed() -> TestResult {
    let source = base()
        .with("ELIBRARY_SMTP_SECURITY", "tls")
        .with("ELIBRARY_SMTP_PORT", "465");
    let settings = SmtpSettings::from_source(&source)?;
    assert_eq!((settings.security, settings.port), (Security::Tls, 465));
    Ok(())
}

#[test]
fn credentials_are_read_from_the_password_file() -> TestResult {
    let dir = std::env::temp_dir().join(format!("smtp-secret-{}", std::process::id()));
    std::fs::write(&dir, "s3cret\n")?;
    let path = dir.to_str().ok_or("path")?;
    let source = base()
        .with("ELIBRARY_SMTP_USER", "mailer")
        .with("ELIBRARY_SMTP_PASSWORD_FILE", path);
    let settings = SmtpSettings::from_source(&source)?;
    std::fs::remove_file(&dir)?;
    let (user, password) = settings.credentials.ok_or("credentials")?;
    assert_eq!(user, "mailer");
    assert_eq!(password.expose(), "s3cret");
    let missing = base()
        .with("ELIBRARY_SMTP_USER", "mailer")
        .with("ELIBRARY_SMTP_PASSWORD_FILE", "/nonexistent/smtp-secret");
    assert!(matches!(
        SmtpSettings::from_source(&missing),
        Err(ConfigError::SecretUnreadable { .. })
    ));
    Ok(())
}

fn reply(stream: &mut TcpStream, text: &str) -> std::io::Result<()> {
    stream.write_all(text.as_bytes())
}

fn with_newline(chunk: std::io::Result<Vec<u8>>) -> std::io::Result<Vec<u8>> {
    let mut line = chunk?;
    line.push(b'\n');
    Ok(line)
}

fn read_data(reader: &mut BufReader<TcpStream>) -> std::io::Result<Vec<u8>> {
    let lines = reader.split(b'\n').map(with_newline);
    let body = lines.take_while(|line| line.as_ref().is_ok_and(|text| text != b".\r\n"));
    body.collect::<std::io::Result<Vec<_>>>()
        .map(|lines| lines.concat())
}

/// Answer for one command, and whether the session continues.
fn answer(command: &str, rcpt_reply: &str) -> (String, bool) {
    let upper = command.to_ascii_uppercase();
    if upper.starts_with("RCPT") {
        (rcpt_reply.to_owned(), true)
    } else if upper.starts_with("QUIT") {
        ("221 bye\r\n".to_owned(), false)
    } else if upper.starts_with("EHLO") {
        ("250 localhost\r\n".to_owned(), true)
    } else {
        ("250 ok\r\n".to_owned(), true)
    }
}

struct Conn {
    reader: BufReader<TcpStream>,
    writer: TcpStream,
    rcpt_reply: String,
    captured: Vec<u8>,
}

fn next_line(reader: &mut BufReader<TcpStream>) -> std::io::Result<Option<String>> {
    let mut line = String::new();
    let read = reader.read_line(&mut line)?;
    Ok((read > 0).then_some(line))
}

/// Handles one command line; false when the session is over.
fn dispatch(line: &str, conn: &mut Conn) -> std::io::Result<bool> {
    if line.to_ascii_uppercase().starts_with("DATA") {
        reply(&mut conn.writer, "354 go\r\n")?;
        conn.captured = read_data(&mut conn.reader)?;
        reply(&mut conn.writer, "250 queued\r\n")?;
        return Ok(true);
    }
    let (text, more) = answer(line, &conn.rcpt_reply);
    reply(&mut conn.writer, &text)?;
    Ok(more)
}

fn run(conn: &mut Conn) -> std::io::Result<()> {
    let Some(line) = next_line(&mut conn.reader)? else {
        return Ok(());
    };
    if dispatch(&line, conn)? {
        run(conn)
    } else {
        Ok(())
    }
}

fn session(stream: TcpStream, rcpt_reply: &str) -> std::io::Result<Vec<u8>> {
    let mut writer = stream.try_clone()?;
    reply(&mut writer, "220 fake ready\r\n")?;
    let mut conn = Conn {
        reader: BufReader::new(stream),
        writer,
        rcpt_reply: rcpt_reply.to_owned(),
        captured: Vec::new(),
    };
    run(&mut conn)?;
    Ok(conn.captured)
}

fn serve(listener: &TcpListener, rcpt_reply: &str, sender: &Sender<Vec<u8>>) {
    if let Ok((stream, _)) = listener.accept() {
        let data = session(stream, rcpt_reply).unwrap_or_default();
        drop(sender.send(data));
    }
}

type Fake = (u16, Receiver<Vec<u8>>, JoinHandle<()>);

fn fake_server(rcpt_reply: &'static str) -> Result<Fake, Box<dyn Error>> {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let port = listener.local_addr()?.port();
    let (sender, receiver) = channel();
    let handle = std::thread::spawn(move || {
        serve(&listener, rcpt_reply, &sender);
    });
    Ok((port, receiver, handle))
}

fn transport(port: u16) -> Result<SmtpTransport, Box<dyn Error>> {
    let settings = SmtpSettings {
        host: "127.0.0.1".to_owned(),
        port,
        from: "ELibrary <noreply@example.org>".to_owned(),
        security: Security::Plain,
        credentials: None,
    };
    Ok(SmtpTransport::new(&settings)?)
}

fn mail() -> OutgoingMail {
    OutgoingMail {
        to: "reader@example.org".to_owned(),
        subject: "Welcome".to_owned(),
        text: "স্বাগতম, বই পড়ুন\r\nhttps://example.org/x".to_owned(),
    }
}

fn qp_byte(first: u8, tail: &[u8]) -> (u8, usize) {
    let hex = tail
        .get(..2)
        .and_then(|pair| std::str::from_utf8(pair).ok());
    let value = hex.and_then(|pair| u8::from_str_radix(pair, 16).ok());
    value
        .filter(|_| first == b'=')
        .map_or((first, 0), |byte| (byte, 2))
}

fn decode_into(rest: &[u8], out: &mut Vec<u8>) {
    let Some((&first, tail)) = rest.split_first() else {
        return;
    };
    let (byte, used) = qp_byte(first, tail);
    out.push(byte);
    decode_into(tail.get(used..).unwrap_or_default(), out);
}

fn decode_qp(raw: &str) -> Vec<u8> {
    let mut out = Vec::new();
    decode_into(raw.replace("=\r\n", "").as_bytes(), &mut out);
    out
}

#[tokio::test]
async fn a_mail_is_delivered_with_recipient_subject_and_bengali_body() -> TestResult {
    let (port, received, handle) = fake_server("250 ok\r\n")?;
    transport(port)?
        .send(&mail())
        .await
        .map_err(|e| format!("{e:?}"))?;
    let data = String::from_utf8(received.recv()?)?;
    handle.join().map_err(|_| "server thread")?;
    assert!(data.contains("Subject: Welcome"));
    assert!(data.contains("reader@example.org"));
    assert!(data.to_ascii_lowercase().contains("charset=utf-8"));
    let body = data.split("\r\n\r\n").nth(1).ok_or("body")?;
    let decoded = String::from_utf8(decode_qp(body))?;
    assert!(decoded.contains("স্বাগতম, বই পড়ুন"));
    assert!(decoded.contains("https://example.org/x"));
    Ok(())
}

#[tokio::test]
async fn a_550_recipient_rejection_is_permanent() -> TestResult {
    let (port, _received, _handle) = fake_server("550 no such user\r\n")?;
    let result = transport(port)?.send(&mail()).await;
    assert_eq!(result, Err(SendError::Permanent));
    Ok(())
}

#[tokio::test]
async fn a_451_reply_is_retryable() -> TestResult {
    let (port, _received, _handle) = fake_server("451 try later\r\n")?;
    let result = transport(port)?.send(&mail()).await;
    assert_eq!(result, Err(SendError::Retryable));
    Ok(())
}

#[tokio::test]
async fn a_closed_port_is_retryable() -> TestResult {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let port = listener.local_addr()?.port();
    drop(listener);
    let result = transport(port)?.send(&mail()).await;
    assert_eq!(result, Err(SendError::Retryable));
    Ok(())
}

#[tokio::test]
async fn a_malformed_recipient_is_permanent() -> TestResult {
    let bad = OutgoingMail {
        to: "not an address".to_owned(),
        ..mail()
    };
    let result = transport(1)?.send(&bad).await;
    assert_eq!(result, Err(SendError::Permanent));
    Ok(())
}

#[test]
fn the_transport_refuses_plain_for_a_public_host() {
    let settings = SmtpSettings {
        host: "smtp.example.org".to_owned(),
        port: 25,
        from: "noreply@example.org".to_owned(),
        security: Security::Plain,
        credentials: None,
    };
    assert!(SmtpTransport::new(&settings).is_err());
}
