use std::time::Duration;

use platform_time::{Clock, Instant, SystemClock};

#[test]
fn unix_seconds_round_trip() {
    let instant = Instant::from_unix_seconds(1_800_000_000);
    assert_eq!(instant.map(|i| i.unix_seconds()), Some(1_800_000_000));
}

#[test]
fn checked_add_moves_forward_and_detects_overflow() {
    let start = Instant::from_unix_seconds(0);
    let later = start.and_then(|s| s.checked_add(Duration::from_secs(90)));
    assert_eq!(later.map(|i| i.unix_seconds()), Some(90));
    assert_eq!(start.and_then(|s| s.checked_add(Duration::MAX)), None);
}

#[test]
fn system_clock_is_not_before_2026() {
    let floor = Instant::from_unix_seconds(1_767_225_600);
    assert!(floor.is_some_and(|floor| SystemClock.now() > floor));
}
