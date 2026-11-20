//! The background loop: pull new mail events from identity, then send what is due. A failure in
//! one round is logged by class only and the next round tries again (REQ-NTF-001, 002, 008).

use std::time::Duration;

use platform_internal_http::Caller;
use platform_time::{Clock, SystemClock};
use sqlx::PgPool;

use crate::puller::{Hub, Source, pull_all};
use crate::sender::{Deps, send_due};
use crate::transport::MailTransport;

const ROUND_PAUSE: Duration = Duration::from_secs(5);

/// Everything one notify instance needs to run its loop.
pub struct Loops<T: MailTransport> {
    pub pool: PgPool,
    pub caller: Caller,
    pub identity_base: String,
    pub transport: T,
}

/// What one round did.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Round {
    pub pulled: usize,
    pub handled: usize,
}

/// One pull-then-send round; a failing half is logged and counts as zero.
pub async fn round<T: MailTransport>(loops: &Loops<T>) -> Round {
    let now = SystemClock.now();
    let hub = Hub {
        pool: &loops.pool,
        caller: &loops.caller,
    };
    let source = Source {
        name: "identity",
        base: &loops.identity_base,
    };
    let pulled = pull_all(hub, source, now).await.unwrap_or_else(|error| {
        tracing::warn!(%error, "pulling mail events failed");
        0
    });
    let deps = Deps {
        pool: &loops.pool,
        caller: &loops.caller,
        identity_base: &loops.identity_base,
        transport: &loops.transport,
    };
    let handled = send_due(&deps, now).await.unwrap_or_else(|error| {
        tracing::warn!(%error, "sending mail failed");
        0
    });
    Round { pulled, handled }
}

/// Runs rounds for as long as the process lives.
pub async fn run<T: MailTransport>(loops: Loops<T>) {
    loop {
        round(&loops).await;
        tokio::time::sleep(ROUND_PAUSE).await;
    }
}
