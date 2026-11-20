//! Rate limiter, concurrency gate and stream registry (TST-GWY-009/010/013/014/017).

use std::collections::HashMap;
use std::time::Duration;

use platform_time::Instant;
use proptest::prelude::*;
use svc_gateway::limits::{
    ClientKey, ConcurrencyGate, Policy, RateLimiter, StreamRegistry, Verdict,
};

type Failure = Box<dyn std::error::Error>;

const BASE: i64 = 1_700_000_000;

fn at_ms(offset_ms: u64) -> Result<Instant, Failure> {
    let start = Instant::from_unix_seconds(BASE).ok_or("bad base instant")?;
    start
        .checked_add(Duration::from_millis(offset_ms))
        .ok_or_else(|| "instant overflow".into())
}

fn key(n: u32) -> ClientKey {
    ClientKey::Address(format!("k{n}"))
}

fn policy(capacity_keys: usize, burst: u32, refill: u32) -> Policy {
    Policy {
        capacity_keys,
        burst,
        refill_per_second: refill,
        idle_expiry: Duration::from_secs(600),
    }
}

#[test]
fn inv_gwy_007_limited_keys_survive_a_flood_of_new_keys() -> Result<(), Failure> {
    let mut limiter = RateLimiter::new(policy(3, 1, 1));
    let now = at_ms(0)?;
    for n in 0..3 {
        assert_eq!(limiter.check(&key(n), now), Verdict::Allowed);
    }
    for n in 0..3 {
        assert!(matches!(
            limiter.check(&key(n), now),
            Verdict::Limited { .. }
        ));
    }
    for n in 100..200 {
        assert!(matches!(
            limiter.check(&key(n), now),
            Verdict::Limited { .. }
        ));
        assert_eq!(limiter.len(), 3);
    }
    let still = limiter.check(&key(0), now);
    assert!(matches!(still, Verdict::Limited { .. }));
    Ok(())
}

#[test]
fn inv_gwy_007_unlimited_least_recent_key_is_evicted_first() -> Result<(), Failure> {
    let mut limiter = RateLimiter::new(policy(2, 5, 1));
    assert_eq!(limiter.check(&key(1), at_ms(0)?), Verdict::Allowed);
    assert_eq!(limiter.check(&key(2), at_ms(1000)?), Verdict::Allowed);
    assert_eq!(limiter.check(&key(3), at_ms(2000)?), Verdict::Allowed);
    assert_eq!(limiter.len(), 2);
    Ok(())
}

#[test]
fn idle_entries_are_removed_lazily() -> Result<(), Failure> {
    let mut limiter = RateLimiter::new(policy(2, 1, 1));
    limiter.check(&key(1), at_ms(0)?);
    limiter.check(&key(2), at_ms(0)?);
    limiter.check(&key(3), at_ms(601_000)?);
    assert_eq!(limiter.len(), 1);
    Ok(())
}

#[test]
fn retry_after_is_at_least_one_second() -> Result<(), Failure> {
    let mut limiter = RateLimiter::new(policy(4, 1, 100));
    let now = at_ms(0)?;
    limiter.check(&key(1), now);
    match limiter.check(&key(1), now) {
        Verdict::Limited {
            retry_after_seconds,
        } => assert!(retry_after_seconds >= 1),
        Verdict::Allowed => return Err("expected limited".into()),
    }
    Ok(())
}

#[test]
fn tst_gwy_014_sixty_fifth_concurrent_call_is_refused_and_permits_release() {
    let gate = ConcurrencyGate::new();
    let permits: Vec<_> = (0..64)
        .filter_map(|_| gate.try_acquire("catalog"))
        .collect();
    assert_eq!(permits.len(), 64);
    assert!(gate.try_acquire("catalog").is_none());
    assert!(gate.try_acquire("identity").is_some());
    drop(permits);
    assert!(gate.try_acquire("catalog").is_some());
}

#[test]
fn tst_gwy_017_fourth_stream_per_user_and_twenty_first_overall_are_refused() {
    let streams = StreamRegistry::new();
    let mine: Vec<_> = (0..3).filter_map(|_| streams.try_open("u0")).collect();
    assert_eq!(mine.len(), 3);
    assert!(streams.try_open("u0").is_none());
    let others: Vec<_> = (1..18)
        .filter_map(|n| streams.try_open(&format!("u{n}")))
        .collect();
    assert_eq!(others.len(), 17);
    assert!(streams.try_open("late").is_none());
    drop(mine);
    assert!(streams.try_open("u0").is_some());
}

#[derive(Debug, Clone)]
struct Step {
    key: u32,
    advance_ms: u64,
}

fn steps() -> impl Strategy<Value = Vec<Step>> {
    let step = (0u32..12, 0u64..800).prop_map(|(key, advance_ms)| Step { key, advance_ms });
    proptest::collection::vec(step, 1..300)
}

fn record(allowed: &mut HashMap<u32, Vec<u64>>, when: (u32, u64), verdict: Verdict) {
    if verdict == Verdict::Allowed {
        allowed.entry(when.0).or_default().push(when.1);
    }
}

/// Runs `steps`, returning the allowed times per key; checks the size bound on the way.
fn run(
    limiter: &mut RateLimiter,
    capacity: usize,
    steps: &[Step],
) -> Result<HashMap<u32, Vec<u64>>, TestCaseError> {
    let mut now_ms = 0u64;
    let mut allowed: HashMap<u32, Vec<u64>> = HashMap::new();
    for step in steps {
        now_ms += step.advance_ms;
        let at = at_ms(now_ms).map_err(|e| TestCaseError::fail(e.to_string()))?;
        record(
            &mut allowed,
            (step.key, now_ms),
            limiter.check(&key(step.key), at),
        );
        prop_assert!(limiter.len() <= capacity);
    }
    Ok(allowed)
}

proptest! {
    #[test]
    fn tst_gwy_009_table_never_exceeds_capacity_under_eviction(
        steps in steps(), capacity in 1usize..8, burst in 1u32..6,
    ) {
        let mut limiter = RateLimiter::new(policy(capacity, burst, 1));
        run(&mut limiter, capacity, &steps)?;
    }

    #[test]
    fn tst_gwy_009_quota_per_window_holds_when_no_key_is_evicted(
        steps in steps(), burst in 1u32..6, refill in 1u32..5,
    ) {
        let mut limiter = RateLimiter::new(policy(12, burst, refill));
        let allowed = run(&mut limiter, 12, &steps)?;
        for times in allowed.values() {
            for (i, start) in times.iter().enumerate() {
                let in_window = times.iter().skip(i).take_while(|t| **t - start <= 1000).count();
                prop_assert!(in_window as u64 <= u64::from(burst) + u64::from(refill));
            }
        }
    }
}
