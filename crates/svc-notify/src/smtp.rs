//! The SMTP implementation of [`MailTransport`] (REQ-NTF SMTP). TLS is rustls with the web PKI
//! roots; certificate verification cannot be switched off by configuration (D-102). Errors carry
//! only a class: never an address, a link or a server banner.

use std::future::Future;
use std::time::Duration;

use lettre::message::header::ContentType;
use lettre::message::{Body, Mailbox};
use lettre::transport::smtp::AsyncSmtpTransportBuilder;
use lettre::transport::smtp::authentication::Credentials;
use lettre::transport::smtp::client::Tls;
use lettre::{AsyncSmtpTransport, AsyncTransport, Message, Tokio1Executor};
use platform_config::{ConfigError, ConfigSource, Secret, read_secret_file};

use crate::transport::{MailTransport, OutgoingMail, SendError};

const TIMEOUT: Duration = Duration::from_secs(15);
const HOST_KEY: &str = "ELIBRARY_SMTP_HOST";
const PORT_KEY: &str = "ELIBRARY_SMTP_PORT";
const FROM_KEY: &str = "ELIBRARY_SMTP_FROM";
const SECURITY_KEY: &str = "ELIBRARY_SMTP_SECURITY";
const USER_KEY: &str = "ELIBRARY_SMTP_USER";
const PASSWORD_FILE_KEY: &str = "ELIBRARY_SMTP_PASSWORD_FILE";
const DEFAULT_PORT: u16 = 587;

/// How the connection to the relay is protected.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Security {
    /// Plain connection upgraded with STARTTLS (required, never optional).
    StartTls,
    /// TLS from the first byte (implicit TLS).
    Tls,
    /// No encryption; only for loopback and internal dev hosts.
    Plain,
}

/// Where and how to reach the relay.
#[derive(Debug)]
pub struct SmtpSettings {
    pub host: String,
    pub port: u16,
    pub from: String,
    pub security: Security,
    pub credentials: Option<(String, Secret<String>)>,
}

impl SmtpSettings {
    /// Reads the `ELIBRARY_SMTP_*` settings; refuses `plain` for a public host.
    ///
    /// # Errors
    /// A missing or invalid setting, or an unreadable password file.
    pub fn from_source(source: &impl ConfigSource) -> Result<Self, ConfigError> {
        let host = required(source, HOST_KEY)?;
        let from = required(source, FROM_KEY)?;
        let port = parse_port(source)?;
        let security = parse_security(source)?;
        let credentials = parse_credentials(source)?;
        check_plain(&host, security)?;
        Ok(Self {
            host,
            port,
            from,
            security,
            credentials,
        })
    }
}

fn required(source: &impl ConfigSource, key: &str) -> Result<String, ConfigError> {
    source
        .get(key)
        .filter(|value| !value.trim().is_empty())
        .ok_or_else(|| ConfigError::Missing {
            key: key.to_owned(),
        })
}

fn invalid(key: &str) -> ConfigError {
    ConfigError::InvalidValue {
        key: key.to_owned(),
    }
}

fn parse_port(source: &impl ConfigSource) -> Result<u16, ConfigError> {
    let Some(text) = source.get(PORT_KEY) else {
        return Ok(DEFAULT_PORT);
    };
    match text.trim().parse::<u16>() {
        Ok(0) => Err(ConfigError::ZeroPort {
            key: PORT_KEY.to_owned(),
        }),
        Ok(port) => Ok(port),
        Err(_) => Err(invalid(PORT_KEY)),
    }
}

fn parse_security(source: &impl ConfigSource) -> Result<Security, ConfigError> {
    let text = source.get(SECURITY_KEY).unwrap_or_default();
    match text.trim().to_ascii_lowercase().as_str() {
        "" | "starttls" => Ok(Security::StartTls),
        "tls" => Ok(Security::Tls),
        "plain" => Ok(Security::Plain),
        _ => Err(invalid(SECURITY_KEY)),
    }
}

fn parse_credentials(
    source: &impl ConfigSource,
) -> Result<Option<(String, Secret<String>)>, ConfigError> {
    let Some(user) = source.get(USER_KEY).filter(|user| !user.is_empty()) else {
        return Ok(None);
    };
    let password = read_secret_file(source, PASSWORD_FILE_KEY)?;
    Ok(Some((user, password)))
}

/// `plain` is only for loopback, the Compose dev sink and `.internal` names.
fn check_plain(host: &str, security: Security) -> Result<(), ConfigError> {
    let local =
        matches!(host, "localhost" | "127.0.0.1" | "mailpit") || host.ends_with(".internal");
    if security == Security::Plain && !local {
        return Err(invalid(SECURITY_KEY));
    }
    Ok(())
}

/// Sends mails through an SMTP relay.
#[derive(Debug, Clone)]
pub struct SmtpTransport {
    inner: AsyncSmtpTransport<Tokio1Executor>,
    from: Mailbox,
}

impl SmtpTransport {
    /// Builds the transport; no connection is made until the first send.
    ///
    /// # Errors
    /// An invalid sender address, host name or a `plain` setting for a public host.
    pub fn new(settings: &SmtpSettings) -> Result<Self, ConfigError> {
        check_plain(&settings.host, settings.security)?;
        let from = settings.from.parse().map_err(|_| invalid(FROM_KEY))?;
        let builder = base_builder(settings)?
            .port(settings.port)
            .timeout(Some(TIMEOUT));
        let inner = with_credentials(builder, settings).build();
        Ok(Self { inner, from })
    }
}

fn base_builder(settings: &SmtpSettings) -> Result<AsyncSmtpTransportBuilder, ConfigError> {
    let host = settings.host.as_str();
    match settings.security {
        Security::StartTls => AsyncSmtpTransport::<Tokio1Executor>::starttls_relay(host)
            .map_err(|_| invalid(HOST_KEY)),
        Security::Tls => {
            AsyncSmtpTransport::<Tokio1Executor>::relay(host).map_err(|_| invalid(HOST_KEY))
        }
        Security::Plain => {
            Ok(AsyncSmtpTransport::<Tokio1Executor>::builder_dangerous(host).tls(Tls::None))
        }
    }
}

fn with_credentials(
    builder: AsyncSmtpTransportBuilder,
    settings: &SmtpSettings,
) -> AsyncSmtpTransportBuilder {
    match &settings.credentials {
        Some((user, password)) => {
            builder.credentials(Credentials::new(user.clone(), password.expose().clone()))
        }
        None => builder,
    }
}

/// A plain-text UTF-8 message, quoted-printable so Bengali survives any relay.
fn build_message(from: &Mailbox, mail: &OutgoingMail) -> Result<Message, SendError> {
    let to: Mailbox = mail.to.parse().map_err(|_| SendError::Permanent)?;
    let body = Body::new_with_encoding(
        mail.text.clone(),
        lettre::message::header::ContentTransferEncoding::QuotedPrintable,
    )
    .map_err(|_| SendError::Permanent)?;
    Message::builder()
        .from(from.clone())
        .to(to)
        .subject(mail.subject.clone())
        .header(ContentType::TEXT_PLAIN)
        .body(body)
        .map_err(|_| SendError::Permanent)
}

/// 5xx replies are permanent; connection, TLS, timeout and 4xx problems are worth retrying.
fn classify(error: &lettre::transport::smtp::Error) -> SendError {
    if error.is_permanent() {
        SendError::Permanent
    } else {
        SendError::Retryable
    }
}

async fn deliver(
    inner: AsyncSmtpTransport<Tokio1Executor>,
    message: Result<Message, SendError>,
) -> Result<(), SendError> {
    let message = message?;
    let result = inner.send(message).await;
    result.map(|_| ()).map_err(|error| {
        let class = classify(&error);
        tracing::warn!(?class, "smtp send failed");
        class
    })
}

impl MailTransport for SmtpTransport {
    fn send(&self, mail: &OutgoingMail) -> impl Future<Output = Result<(), SendError>> + Send {
        deliver(self.inner.clone(), build_message(&self.from, mail))
    }
}
