//! The only way domain and service code reads the time: inject a [`Clock`].

use std::time::Duration;

use time::OffsetDateTime;

/// A point in time, always UTC (stored as `timestamptz`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct Instant(OffsetDateTime);

impl Instant {
    #[must_use]
    pub fn from_unix_seconds(seconds: i64) -> Option<Self> {
        OffsetDateTime::from_unix_timestamp(seconds).ok().map(Self)
    }

    #[must_use]
    pub fn unix_seconds(&self) -> i64 {
        self.0.unix_timestamp()
    }

    /// `None` when the result is out of the representable range.
    #[must_use]
    pub fn checked_add(&self, duration: Duration) -> Option<Self> {
        self.0.checked_add(duration.try_into().ok()?).map(Self)
    }
}

/// Source of the current time.
pub trait Clock {
    fn now(&self) -> Instant;
}

/// The wall clock.
#[derive(Debug, Clone, Copy, Default)]
pub struct SystemClock;

impl Clock for SystemClock {
    fn now(&self) -> Instant {
        Instant(OffsetDateTime::now_utc())
    }
}
