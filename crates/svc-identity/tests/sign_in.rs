//! Sign-in and sessions against a real Postgres: ignored in a plain `cargo test`; run by
//! `cargo xtask check` (gate Q4).

use std::time::Duration;

use domain_credentials::{Password, PasswordHash, SALT_BYTES};
use platform_random::OsRandom;
use platform_testkit::{FakeClock, TestDatabase};
use platform_time::Clock;
use sqlx::{AssertSqlSafe, PgPool};
use svc_identity::MIGRATIONS;
use svc_identity::session::{self, IDLE_TIMEOUT, IssuedSession, SessionState};
use svc_identity::sign_in::{Client, Credentials, Services, SignInOutcome, sign_in};

type Failure = Box<dyn std::error::Error>;

const PASSWORD: &str = "correct horse battery";
const USER: &str = "00000000-0000-7000-8000-00000000000a";
const START: i64 = 1_800_000_000;

struct World {
    pool: PgPool,
    clock: FakeClock,
    dummy: PasswordHash,
}

async fn world() -> Result<World, Failure> {
    let pool = TestDatabase::create(&MIGRATIONS).await?.pool;
    let dummy = PasswordHash::create(&Password::parse("dummy dummy dummy")?, &[9; SALT_BYTES])?;
    Ok(World {
        pool,
        clock: FakeClock::at_unix_seconds(START),
        dummy,
    })
}

async fn add_user(pool: &PgPool, status: &str, totp_required: bool) -> Result<(), Failure> {
    let hash = PasswordHash::create(&Password::parse(PASSWORD)?, &[3; SALT_BYTES])?;
    sqlx::query(
        "insert into users (id, email, display_name, language, status, role, totp_required, created_at, updated_at)
         values ($1::uuid, 'Reader@Example.org', 'Reader', 'bn', $2, 'reader', $3, now(), now())",
    )
    .bind(USER)
    .bind(status)
    .bind(totp_required)
    .execute(pool)
    .await?;
    sqlx::query(
        "insert into credentials (user_id, password_hash, changed_at) values ($1::uuid, $2, now())",
    )
    .bind(USER)
    .bind(hash.as_str())
    .execute(pool)
    .await?;
    Ok(())
}

async fn attempt(world: &World, email: &str, password: &str) -> Result<SignInOutcome, Failure> {
    let services = Services {
        pool: &world.pool,
        clock: &world.clock,
        random: &OsRandom,
        dummy_hash: &world.dummy,
    };
    Ok(sign_in(
        &services,
        Credentials { email, password },
        Client {
            address: Some("203.0.113.0/24"),
        },
    )
    .await?)
}

fn signed_in(outcome: SignInOutcome) -> Result<IssuedSession, Failure> {
    let description = format!("{outcome:?}");
    match outcome {
        SignInOutcome::SignedIn(issued) => Ok(issued),
        SignInOutcome::SecondFactorRequired(_)
        | SignInOutcome::Rejected
        | SignInOutcome::Throttled => Err(format!("expected SignedIn, got {description}").into()),
    }
}

fn second_factor(outcome: SignInOutcome) -> Result<IssuedSession, Failure> {
    let description = format!("{outcome:?}");
    match outcome {
        SignInOutcome::SecondFactorRequired(issued) => Ok(issued),
        SignInOutcome::SignedIn(_) | SignInOutcome::Rejected | SignInOutcome::Throttled => {
            Err(format!("expected SecondFactorRequired, got {description}").into())
        }
    }
}

async fn wrong_attempts(world: &World, times: usize) -> Result<Vec<SignInOutcome>, Failure> {
    let mut outcomes = Vec::new();
    for _ in 0..times {
        outcomes.push(attempt(world, "reader@example.org", "wrong password here").await?);
    }
    Ok(outcomes)
}

async fn count(pool: &PgPool, sql: &str) -> Result<i64, Failure> {
    // why: fixed test statements, no user input.
    Ok(sqlx::query_scalar(AssertSqlSafe(sql.to_owned()))
        .fetch_one(pool)
        .await?)
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn the_right_password_opens_a_session_whose_token_is_stored_only_as_a_hash()
-> Result<(), Failure> {
    let world = world().await?;
    add_user(&world.pool, "active", false).await?;
    let issued = signed_in(attempt(&world, "reader@example.ORG", PASSWORD).await?)?;
    assert_eq!(issued.token.len(), 64);
    assert_eq!(
        count(&world.pool, "select count(*) from sessions").await?,
        1
    );
    let stored = count(
        &world.pool,
        &format!(
            "select count(*) from sessions where encode(token_hash, 'hex') = '{}'",
            issued.token
        ),
    )
    .await?;
    assert_eq!(stored, 0, "the clear token is never stored");
    assert_eq!(
        count(
            &world.pool,
            "select count(*) from audit_log where action = 'sign_in'"
        )
        .await?,
        1
    );
    let live = session::lookup(&world.pool, &issued.token, world.clock.now()).await?;
    assert_eq!(live.map(|s| s.state), Some(SessionState::Authenticated));
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn unknown_account_wrong_password_and_inactive_account_are_indistinguishable()
-> Result<(), Failure> {
    let world = world().await?;
    add_user(&world.pool, "suspended", false).await?;
    let unknown = attempt(&world, "nobody@example.org", PASSWORD).await?;
    let wrong = attempt(&world, "reader@example.org", "wrong password here").await?;
    let inactive = attempt(&world, "reader@example.org", PASSWORD).await?;
    assert_eq!(
        (unknown, wrong, inactive),
        (
            SignInOutcome::Rejected,
            SignInOutcome::Rejected,
            SignInOutcome::Rejected
        )
    );
    assert_eq!(
        count(&world.pool, "select count(*) from sessions").await?,
        0
    );
    assert_eq!(
        count(
            &world.pool,
            "select count(*) from audit_log where action = 'sign_in_failed'"
        )
        .await?,
        3
    );
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn an_account_that_requires_totp_gets_a_pending_session() -> Result<(), Failure> {
    let world = world().await?;
    add_user(&world.pool, "active", true).await?;
    let issued = second_factor(attempt(&world, "reader@example.org", PASSWORD).await?)?;
    let live = session::lookup(&world.pool, &issued.token, world.clock.now()).await?;
    assert_eq!(live.map(|s| s.state), Some(SessionState::PendingTotp));
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn too_many_attempts_are_throttled_until_the_window_passes() -> Result<(), Failure> {
    let world = world().await?;
    add_user(&world.pool, "active", false).await?;
    assert!(
        wrong_attempts(&world, 10)
            .await?
            .iter()
            .all(|outcome| *outcome == SignInOutcome::Rejected)
    );
    assert_eq!(
        attempt(&world, "reader@example.org", PASSWORD).await?,
        SignInOutcome::Throttled
    );
    world.clock.advance(Duration::from_mins(15));
    assert!(matches!(
        attempt(&world, "reader@example.org", PASSWORD).await?,
        SignInOutcome::SignedIn(_)
    ));
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn sessions_expire_when_idle_and_slide_when_used() -> Result<(), Failure> {
    let world = world().await?;
    add_user(&world.pool, "active", false).await?;
    let issued = signed_in(attempt(&world, "reader@example.org", PASSWORD).await?)?;
    let almost_idle = IDLE_TIMEOUT.saturating_sub(Duration::from_mins(1));
    let found = |clock: &FakeClock| session::lookup(&world.pool, &issued.token, clock.now());
    world.clock.advance(almost_idle);
    assert!(
        found(&world.clock).await?.is_some(),
        "just inside the idle limit"
    );
    world.clock.advance(almost_idle);
    assert!(
        found(&world.clock).await?.is_some(),
        "use slid the idle window"
    );
    world.clock.advance(IDLE_TIMEOUT + Duration::from_secs(1));
    assert!(found(&world.clock).await?.is_none(), "idle for too long");
    Ok(())
}

#[tokio::test]
#[ignore = "needs the test postgres: run `cargo xtask check`"]
async fn revoked_and_unknown_sessions_find_nothing() -> Result<(), Failure> {
    let world = world().await?;
    add_user(&world.pool, "active", false).await?;
    let issued = signed_in(attempt(&world, "reader@example.org", PASSWORD).await?)?;
    session::revoke(&world.pool, &issued.token, world.clock.now()).await?;
    assert!(
        session::lookup(&world.pool, &issued.token, world.clock.now())
            .await?
            .is_none(),
        "revoked"
    );
    assert!(
        session::lookup(&world.pool, "not-a-token", world.clock.now())
            .await?
            .is_none(),
        "unknown token"
    );
    Ok(())
}
