use std::sync::atomic::{AtomicI64, Ordering};
use std::time::Duration;

use platform_time::{Clock, Instant};

/// A clock tests move by hand.
#[derive(Debug)]
pub struct FakeClock(AtomicI64);

impl FakeClock {
    #[must_use]
    pub fn at_unix_seconds(seconds: i64) -> Self {
        Self(AtomicI64::new(seconds))
    }

    pub fn advance(&self, by: Duration) {
        let seconds = i64::try_from(by.as_secs()).unwrap_or(i64::MAX);
        self.0.fetch_add(seconds, Ordering::SeqCst);
    }
}

impl Clock for FakeClock {
    fn now(&self) -> Instant {
        Instant::from_unix_seconds(self.0.load(Ordering::SeqCst))
            .unwrap_or_else(|| Instant::from_offset_date_time(time::OffsetDateTime::UNIX_EPOCH))
    }
}
