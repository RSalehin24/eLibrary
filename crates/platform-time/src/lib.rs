//! The only way domain and service code reads the time: inject a [`Clock`].

use std::time::Duration;

use time::OffsetDateTime;

const NANOS_PER_MILLI: i128 = 1_000_000;

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

    /// Unix milliseconds, never negative (times before 1970 give 0).
    #[must_use]
    pub fn unix_millis(&self) -> u64 {
        u64::try_from(self.0.unix_timestamp_nanos() / NANOS_PER_MILLI).unwrap_or(0)
    }

    /// For database drivers that bind `time::OffsetDateTime`.
    #[must_use]
    pub fn to_offset_date_time(&self) -> OffsetDateTime {
        self.0
    }

    /// Converts any offset to UTC.
    #[must_use]
    pub fn from_offset_date_time(value: OffsetDateTime) -> Self {
        Self(value.to_offset(time::UtcOffset::UTC))
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
