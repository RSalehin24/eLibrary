use std::time::Duration;

use platform_time::Instant;
use sqlx::PgPool;

pub(crate) const WINDOW: Duration = Duration::from_mins(15);
/// Attempts allowed per key per window before sign-in answers `Throttled`.
pub(crate) const MAX_ATTEMPTS: i32 = 10;

/// Counts this attempt and returns how many the key has made in the current window.
pub(crate) async fn record_attempt(
    pool: &PgPool,
    key: &str,
    now: Instant,
) -> Result<i32, sqlx::Error> {
    let window = i64::try_from(WINDOW.as_secs()).unwrap_or(i64::MAX);
    let start = now.unix_seconds().div_euclid(window) * window;
    let window_start = Instant::from_unix_seconds(start).unwrap_or(now);
    sqlx::query_scalar(
        "insert into login_attempts (key, window_start, count) values ($1, $2, 1)
         on conflict (key, window_start) do update set count = login_attempts.count + 1
         returning count",
    )
    .bind(key)
    .bind(window_start.to_offset_date_time())
    .fetch_one(pool)
    .await
}
