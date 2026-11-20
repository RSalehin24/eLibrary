//! The retry schedule for mail delivery (REQ-NTF-008): pure, no IO.

use std::time::Duration;

use crate::transport::SendError;

/// Attempts after which a still-failing mail is marked failed.
pub const MAX_ATTEMPTS: i32 = 6;

const MINUTE: u64 = 60;
const HOUR: u64 = 60 * MINUTE;

/// Waits after failed attempt 1, 2, 3, 4 and 5.
const BACKOFF: [u64; 5] = [MINUTE, 5 * MINUTE, 30 * MINUTE, 2 * HOUR, 6 * HOUR];

/// What to do after a failed attempt.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Step {
    /// Queue the mail again after this wait.
    RetryAfter(Duration),
    /// Give up: the mail is marked failed.
    Fail,
}

/// The next step after `attempts_done` (1-based, including the failed one) attempts ended in
/// `error`. Permanent errors and exhausted attempts fail.
#[must_use]
pub fn next_step(attempts_done: i32, error: SendError) -> Step {
    match error {
        SendError::Permanent => Step::Fail,
        SendError::Retryable => backoff(attempts_done),
    }
}

fn backoff(attempts_done: i32) -> Step {
    if attempts_done >= MAX_ATTEMPTS {
        return Step::Fail;
    }
    let index = usize::try_from(attempts_done.saturating_sub(1)).unwrap_or(0);
    BACKOFF.get(index).map_or(Step::Fail, |seconds| {
        Step::RetryAfter(Duration::from_secs(*seconds))
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn minutes(n: u64) -> Step {
        Step::RetryAfter(Duration::from_secs(n * 60))
    }

    #[test]
    fn schedule_table() {
        let table = [
            (1, minutes(1)),
            (2, minutes(5)),
            (3, minutes(30)),
            (4, minutes(120)),
            (5, minutes(360)),
            (6, Step::Fail),
            (7, Step::Fail),
        ];
        let got = table.map(|(done, _)| next_step(done, SendError::Retryable));
        assert_eq!(got, table.map(|(_, expected)| expected));
    }

    #[test]
    fn permanent_fails_at_once() {
        let all = (1..=MAX_ATTEMPTS).all(|n| next_step(n, SendError::Permanent) == Step::Fail);
        assert!(all);
    }

    fn delay(done: i32) -> Option<Duration> {
        match next_step(done, SendError::Retryable) {
            Step::RetryAfter(wait) => Some(wait),
            Step::Fail => None,
        }
    }

    #[test]
    fn delays_grow() {
        let delays: Vec<Option<Duration>> = (1..MAX_ATTEMPTS).map(delay).collect();
        assert!(delays.iter().all(Option::is_some));
        assert!(delays.windows(2).all(|pair| pair.first() < pair.get(1)));
    }

    #[test]
    fn nonsense_counts_do_not_panic() {
        assert_eq!(next_step(0, SendError::Retryable), minutes(1));
        assert_eq!(next_step(-3, SendError::Retryable), minutes(1));
    }
}
