//! How a mail leaves the service: a trait with an SMTP implementation (`smtp`) and an in-memory
//! sink for dev and tests. A failure carries only a class, never an address or a link.

use std::future::Future;
use std::sync::{Arc, Mutex};

/// One mail, fully rendered. Lives in memory only for the duration of one send.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OutgoingMail {
    pub to: String,
    pub subject: String,
    pub text: String,
}

/// Why a send failed; the class decides whether it is retried (REQ-NTF-008).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SendError {
    /// Worth trying again later (connection, timeout, 4xx).
    Retryable,
    /// Never worth retrying (bad address, 5xx rejection).
    Permanent,
}

/// Sends mails. Implementations must apply their own timeout.
pub trait MailTransport: Send + Sync {
    fn send(&self, mail: &OutgoingMail) -> impl Future<Output = Result<(), SendError>> + Send;
}

/// Keeps every mail in memory; for dev and tests. It can be told to fail.
#[derive(Debug, Clone, Default)]
pub struct SinkTransport {
    sent: Arc<Mutex<Vec<OutgoingMail>>>,
    failure: Arc<Mutex<Option<SendError>>>,
}

impl SinkTransport {
    /// Every mail accepted so far.
    #[must_use]
    pub fn sent(&self) -> Vec<OutgoingMail> {
        self.sent
            .lock()
            .map_or_else(|_| Vec::new(), |list| list.clone())
    }

    /// Makes the next sends fail with `error` (`None` to succeed again).
    pub fn fail_with(&self, error: Option<SendError>) {
        set(&self.failure, error);
    }
}

fn set(slot: &Mutex<Option<SendError>>, error: Option<SendError>) {
    match slot.lock() {
        Ok(mut guard) => *guard = error,
        Err(poisoned) => *poisoned.into_inner() = error,
    }
}

fn record(list: &Mutex<Vec<OutgoingMail>>, mail: &OutgoingMail) {
    match list.lock() {
        Ok(mut guard) => guard.push(mail.clone()),
        Err(poisoned) => poisoned.into_inner().push(mail.clone()),
    }
}

impl SinkTransport {
    fn deliver(&self, mail: &OutgoingMail) -> Result<(), SendError> {
        let failure = self.failure.lock().map_or(None, |slot| *slot);
        failure
            .map_or(Ok(()), Err)
            .inspect(|()| record(&self.sent, mail))
    }
}

impl MailTransport for SinkTransport {
    fn send(&self, mail: &OutgoingMail) -> impl Future<Output = Result<(), SendError>> + Send {
        std::future::ready(self.deliver(mail))
    }
}
