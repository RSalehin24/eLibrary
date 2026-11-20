//! Gateway limits: bounded in-memory rate tables, the per-upstream concurrency gate and the
//! open-stream registry (REQ-GWY-007, REQ-GWY-010, REQ-GWY-013, INV-GWY-007). Time is always
//! injected as a [`platform_time::Instant`]; nothing here reads a clock.

use std::collections::HashMap;
use std::sync::{Arc, Mutex, MutexGuard, PoisonError};
use std::time::Duration;

use platform_time::Instant;

/// Concurrent requests per upstream (limits table, provisional D-88).
pub const UPSTREAM_CONCURRENCY: usize = 64;
/// Open SSE streams in total (limits table, provisional D-88).
pub const STREAMS_TOTAL: usize = 20;
/// Open SSE streams per user (limits table, provisional D-88).
pub const STREAMS_PER_USER: usize = 3;

/// Maximum keys per rate table (documented gateway constant; not in the limits table).
pub const TABLE_CAPACITY_KEYS: usize = 10_000;
/// Idle time after which a rate entry is dropped (documented gateway constant).
pub const IDLE_EXPIRY: Duration = Duration::from_secs(600);
/// Anonymous per-address rate: 20 req/s, burst 60 (limits table).
pub const ANONYMOUS_BURST: u32 = 60;
/// Anonymous refill per second (limits table).
pub const ANONYMOUS_REFILL: u32 = 20;
/// Authentication routes burst (documented gateway constant, stricter than anonymous).
pub const AUTH_BURST: u32 = 10;
/// Authentication routes refill per second (documented gateway constant).
pub const AUTH_REFILL: u32 = 1;
/// Authenticated subject burst (documented gateway constant).
pub const SUBJECT_BURST: u32 = 120;
/// Authenticated subject refill per second (documented gateway constant).
pub const SUBJECT_REFILL: u32 = 40;

const MILLI: u64 = 1000;

/// Who a bucket belongs to.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum ClientKey {
    /// An already-truncated client address prefix.
    Address(String),
    /// An authenticated subject id.
    Subject(String),
}

/// Shape of one rate table.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Policy {
    /// Maximum number of keys held at once.
    pub capacity_keys: usize,
    /// Bucket size in requests.
    pub burst: u32,
    /// Requests regained per second.
    pub refill_per_second: u32,
    /// Idle time after which an entry is removed.
    pub idle_expiry: Duration,
}

/// The three policies: anonymous, authentication routes, subject (in that order).
#[must_use]
pub fn gateway_policies() -> [Policy; 3] {
    let make = |burst, refill_per_second| Policy {
        capacity_keys: TABLE_CAPACITY_KEYS,
        burst,
        refill_per_second,
        idle_expiry: IDLE_EXPIRY,
    };
    [
        make(ANONYMOUS_BURST, ANONYMOUS_REFILL),
        make(AUTH_BURST, AUTH_REFILL),
        make(SUBJECT_BURST, SUBJECT_REFILL),
    ]
}

/// Answer of [`RateLimiter::check`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Verdict {
    /// The request may proceed.
    Allowed,
    /// Answer 429 with this `Retry-After` (always at least 1).
    Limited {
        /// Seconds to wait.
        retry_after_seconds: u64,
    },
}

#[derive(Debug, Clone, Copy)]
struct Bucket {
    /// Tokens times 1000, so refill is exact in whole milliseconds.
    milli_tokens: u64,
    last_ms: u64,
}

impl Bucket {
    fn refilled(&self, policy: &Policy, now_ms: u64) -> u64 {
        let elapsed = now_ms.saturating_sub(self.last_ms);
        let gained = elapsed.saturating_mul(u64::from(policy.refill_per_second));
        self.milli_tokens
            .saturating_add(gained)
            .min(u64::from(policy.burst) * MILLI)
    }

    fn is_limited(&self, policy: &Policy, now_ms: u64) -> bool {
        self.refilled(policy, now_ms) < MILLI
    }
}

fn spend(bucket: &mut Bucket, policy: &Policy, now_ms: u64) -> Verdict {
    let tokens = bucket.refilled(policy, now_ms);
    bucket.last_ms = bucket.last_ms.max(now_ms);
    if tokens >= MILLI {
        bucket.milli_tokens = tokens - MILLI;
        return Verdict::Allowed;
    }
    bucket.milli_tokens = tokens;
    limited(policy, MILLI - tokens)
}

fn limited(policy: &Policy, deficit_milli: u64) -> Verdict {
    let rate = u64::from(policy.refill_per_second).max(1);
    let wait_ms = deficit_milli.div_ceil(rate);
    Verdict::Limited {
        retry_after_seconds: wait_ms.div_ceil(MILLI).max(1),
    }
}

/// A bounded token-bucket table (one per traffic class).
#[derive(Debug)]
pub struct RateLimiter {
    policy: Policy,
    buckets: HashMap<ClientKey, Bucket>,
}

impl RateLimiter {
    /// An empty table.
    #[must_use]
    pub fn new(policy: Policy) -> Self {
        Self {
            policy,
            buckets: HashMap::new(),
        }
    }

    /// Number of keys currently held (never above `capacity_keys`).
    #[must_use]
    pub fn len(&self) -> usize {
        self.buckets.len()
    }

    /// Whether the table holds no keys.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.buckets.is_empty()
    }

    /// Spends one token of `key` at `now`, or says how long to wait.
    pub fn check(&mut self, key: &ClientKey, now: Instant) -> Verdict {
        check_key(self, key, now.unix_millis())
    }
}

fn check_key(table: &mut RateLimiter, key: &ClientKey, now_ms: u64) -> Verdict {
    let policy = table.policy;
    if let Some(bucket) = table.buckets.get_mut(key) {
        return spend(bucket, &policy, now_ms);
    }
    if !make_room(table, now_ms) {
        return limited(&policy, MILLI);
    }
    let mut bucket = Bucket {
        milli_tokens: u64::from(policy.burst) * MILLI,
        last_ms: now_ms,
    };
    let verdict = spend(&mut bucket, &policy, now_ms);
    table.buckets.insert(key.clone(), bucket);
    verdict
}

/// Frees one slot if the table is full; `false` when every entry is limited.
fn make_room(table: &mut RateLimiter, now_ms: u64) -> bool {
    if table.buckets.len() < table.policy.capacity_keys {
        return true;
    }
    drop_idle(table, now_ms);
    if table.buckets.len() < table.policy.capacity_keys {
        return true;
    }
    evict_least_recent_unlimited(table, now_ms)
}

fn drop_idle(table: &mut RateLimiter, now_ms: u64) {
    let idle_ms = u64::try_from(table.policy.idle_expiry.as_millis()).unwrap_or(u64::MAX);
    table
        .buckets
        .retain(|_, bucket| now_ms.saturating_sub(bucket.last_ms) < idle_ms);
}

fn evict_least_recent_unlimited(table: &mut RateLimiter, now_ms: u64) -> bool {
    let policy = table.policy;
    let victim = table
        .buckets
        .iter()
        .filter(|(_, bucket)| !bucket.is_limited(&policy, now_ms))
        .min_by_key(|(_, bucket)| bucket.last_ms)
        .map(|(key, _)| key.clone());
    victim.is_some_and(|key| table.buckets.remove(&key).is_some())
}

fn lock<T>(mutex: &Mutex<T>) -> MutexGuard<'_, T> {
    mutex.lock().unwrap_or_else(PoisonError::into_inner)
}

/// Per-upstream in-flight counter.
#[derive(Debug, Clone, Default)]
pub struct ConcurrencyGate {
    in_flight: Arc<Mutex<HashMap<String, usize>>>,
}

/// One in-flight upstream call; released on drop.
#[derive(Debug)]
pub struct Permit {
    in_flight: Arc<Mutex<HashMap<String, usize>>>,
    upstream: String,
}

impl ConcurrencyGate {
    /// An empty gate.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Takes a slot for `upstream`; `None` at the limit (answer 503).
    #[must_use]
    pub fn try_acquire(&self, upstream: &str) -> Option<Permit> {
        acquire(&self.in_flight, upstream)
    }
}

fn acquire(in_flight: &Arc<Mutex<HashMap<String, usize>>>, upstream: &str) -> Option<Permit> {
    let mut map = lock(in_flight);
    let count = map.entry(upstream.to_owned()).or_insert(0);
    if *count >= UPSTREAM_CONCURRENCY {
        return None;
    }
    *count += 1;
    Some(Permit {
        in_flight: Arc::clone(in_flight),
        upstream: upstream.to_owned(),
    })
}

fn release(in_flight: &Mutex<HashMap<String, usize>>, upstream: &str) {
    let mut map = lock(in_flight);
    let left = map.get(upstream).copied().unwrap_or(0).saturating_sub(1);
    if left == 0 {
        map.remove(upstream);
    } else {
        map.insert(upstream.to_owned(), left);
    }
}

impl Drop for Permit {
    fn drop(&mut self) {
        release(&self.in_flight, &self.upstream);
    }
}

#[derive(Debug, Default)]
struct StreamCounts {
    total: usize,
    per_user: HashMap<String, usize>,
}

/// Open-stream limits: [`STREAMS_TOTAL`] overall and [`STREAMS_PER_USER`] per user.
#[derive(Debug, Clone, Default)]
pub struct StreamRegistry {
    counts: Arc<Mutex<StreamCounts>>,
}

/// One open stream; released on drop.
#[derive(Debug)]
pub struct StreamGuard {
    counts: Arc<Mutex<StreamCounts>>,
    user: String,
}

impl StreamRegistry {
    /// An empty registry.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Opens a stream for `user`; `None` over either limit (answer 429).
    #[must_use]
    pub fn try_open(&self, user: &str) -> Option<StreamGuard> {
        open_stream(&self.counts, user)
    }
}

fn open_stream(shared: &Arc<Mutex<StreamCounts>>, user: &str) -> Option<StreamGuard> {
    let mut counts = lock(shared);
    let mine = counts.per_user.get(user).copied().unwrap_or(0);
    if counts.total >= STREAMS_TOTAL || mine >= STREAMS_PER_USER {
        return None;
    }
    counts.total += 1;
    counts.per_user.insert(user.to_owned(), mine + 1);
    Some(StreamGuard {
        counts: Arc::clone(shared),
        user: user.to_owned(),
    })
}

fn close_stream(shared: &Mutex<StreamCounts>, user: &str) {
    let mut counts = lock(shared);
    counts.total = counts.total.saturating_sub(1);
    let left = counts
        .per_user
        .get(user)
        .copied()
        .unwrap_or(0)
        .saturating_sub(1);
    if left == 0 {
        counts.per_user.remove(user);
    } else {
        counts.per_user.insert(user.to_owned(), left);
    }
}

impl Drop for StreamGuard {
    fn drop(&mut self) {
        close_stream(&self.counts, &self.user);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn at(seconds: i64) -> Result<Instant, String> {
        Instant::from_unix_seconds(seconds).ok_or_else(|| "bad instant".to_owned())
    }

    fn key(name: &str) -> ClientKey {
        ClientKey::Address(name.to_owned())
    }

    #[test]
    fn inv_gwy_007_burst_then_limited_then_refilled() -> Result<(), String> {
        let mut limiter = RateLimiter::new(Policy {
            capacity_keys: 2,
            burst: 2,
            refill_per_second: 1,
            idle_expiry: Duration::from_secs(60),
        });
        let (a, t) = (key("a"), at(1000)?);
        assert_eq!(limiter.check(&a, t), Verdict::Allowed);
        assert_eq!(limiter.check(&a, t), Verdict::Allowed);
        assert_eq!(
            limiter.check(&a, t),
            Verdict::Limited {
                retry_after_seconds: 1
            }
        );
        assert_eq!(limiter.check(&a, at(1001)?), Verdict::Allowed);
        Ok(())
    }

    #[test]
    fn zero_refill_still_reports_at_least_one_second() {
        let policy = Policy {
            capacity_keys: 1,
            burst: 0,
            refill_per_second: 0,
            idle_expiry: Duration::from_secs(1),
        };
        assert!(matches!(
            limited(&policy, 1),
            Verdict::Limited {
                retry_after_seconds: 1..
            }
        ));
    }

    #[test]
    fn policies_are_stricter_for_anonymous_and_auth_than_subject() {
        let [anonymous, auth, subject] = gateway_policies();
        assert!(auth.burst < anonymous.burst && anonymous.burst < subject.burst);
        assert!(auth.refill_per_second < anonymous.refill_per_second);
    }
}
