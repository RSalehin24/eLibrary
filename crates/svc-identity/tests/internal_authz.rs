//! `authorize` and `check` against a real Postgres: ignored in a plain `cargo test`.

use platform_testkit::TestDatabase;
use platform_time::{Clock, Instant, SystemClock};
use sqlx::PgPool;
use svc_identity::MIGRATIONS;
use svc_identity::internal_authz::{
    Authorization, AuthorizeRequest, AuthzDenial, BookState, CheckRequest, CheckResult, authorize,
    check,
};
use svc_identity::session::{self, IssuedSession, SessionState};
use uuid::Uuid;

type Failure = Box<dyn std::error::Error>;

const USER: &str = "00000000-0000-7000-8000-00000000000a";
const ADMIN: &str = "00000000-0000-7000-8000-00000000000b";
const BOOK: &str = "00000000-0000-7000-8000-0000000000b1";

fn id(text: &str) -> Result<Uuid, Failure> {
    Ok(Uuid::parse_str(text)?)
}

fn now() -> Instant {
    SystemClock.now()
}

async fn pool() -> Result<PgPool, Failure> {
    let pool = TestDatabase::create(&MIGRATIONS).await?.pool;
    for (user, status) in [(USER, "active"), (ADMIN, "active")] {
        sqlx::query(
            "insert into users (id, email, display_name, language, status, role, totp_required, created_at, updated_at)
             values ($1::uuid, $1 || '@example.org', 'U', 'en', $2, 'reader', false, now(), now())",
        )
        .bind(user)
        .bind(status)
        .execute(&pool)
        .await?;
    }
    Ok(pool)
}

async fn session_for(pool: &PgPool, state: SessionState) -> Result<IssuedSession, Failure> {
    let token = format!("token-{}", Uuid::from_u128(rand_seed()));
    let csrf_token = session::csrf_token_for(&token);
    let stored = match state {
        SessionState::PendingTotp => "pending_totp",
        SessionState::Authenticated => "authenticated",
    };
    sqlx::query(
        "insert into sessions (id, token_hash, user_id, state, csrf_hash, created_at, last_seen_at, expires_at)
         values (gen_random_uuid(), sha256(convert_to($1, 'UTF8')), $2::uuid, $3,
                 sha256(convert_to($4, 'UTF8')), now(), now(), now() + interval '1 day')",
    )
    .bind(&token)
    .bind(USER)
    .bind(stored)
    .bind(&csrf_token)
    .execute(pool)
    .await?;
    Ok(IssuedSession {
        user_id: id(USER)?,
        token,
        csrf_token,
        state,
        expires_at: now(),
    })
}

fn request(method: &str, issued: &IssuedSession, csrf: Option<String>) -> AuthorizeRequest {
    AuthorizeRequest {
        method: method.to_owned(),
        path: "/api/x".to_owned(),
        cookie_token: Some(issued.token.clone()),
        origin: None,
        csrf_token: csrf,
    }
}

async fn grant(pool: &PgPool, target: (&str, Option<&str>), hours: i64) -> Result<(), Failure> {
    sqlx::query(
        "insert into grants (id, user_id, scope, book_id, expires_at, granted_by, reason, created_at)
         values (gen_random_uuid(), $1::uuid, $2, $3::uuid, now() + make_interval(hours => $4::int), $5::uuid, 'test', now())",
    )
    .bind(USER)
    .bind(target.0)
    .bind(target.1)
    .bind(i32::try_from(hours)?)
    .bind(ADMIN)
    .execute(pool)
    .await?;
    Ok(())
}

fn ask(scope: &str, book: Option<&str>) -> Result<CheckRequest, Failure> {
    Ok(CheckRequest {
        user_id: id(USER)?,
        scope: scope.to_owned(),
        book_id: book.map(id).transpose()?,
        book_state: book.map(|_| BookState {
            published: true,
            deleted: false,
        }),
    })
}

fn allowed(got: Authorization) -> Result<(Uuid, Vec<&'static str>, i64), Failure> {
    match got {
        Authorization::Allow {
            user_id,
            scopes,
            grant_version,
        } => Ok((user_id, scopes, grant_version)),
        Authorization::NoSession | Authorization::Denied { .. } => {
            Err(format!("not allowed: {got:?}").into())
        }
    }
}

fn deny(reason: &'static str) -> CheckResult {
    CheckResult::Deny { reason }
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn authorize_allows_with_scopes() -> Result<(), Failure> {
    let pool = pool().await?;
    let issued = session_for(&pool, SessionState::Authenticated).await?;
    let got = authorize(&pool, &request("GET", &issued, None), now()).await?;
    let (user_id, scopes, grant_version) = allowed(got)?;
    assert_eq!(user_id, id(USER)?);
    assert!(scopes.contains(&"browse") && !scopes.contains(&"manage_users"));
    assert_eq!(grant_version, 0);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn authorize_without_a_session_is_401() -> Result<(), Failure> {
    let pool = pool().await?;
    let issued = session_for(&pool, SessionState::Authenticated).await?;
    let mut missing = request("GET", &issued, None);
    missing.cookie_token = None;
    assert_eq!(
        authorize(&pool, &missing, now()).await?,
        Authorization::NoSession
    );
    missing.cookie_token = Some("unknown".to_owned());
    assert_eq!(
        authorize(&pool, &missing, now()).await?,
        Authorization::NoSession
    );
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn authorize_denies_pending_totp_and_suspended() -> Result<(), Failure> {
    let pool = pool().await?;
    let pending = session_for(&pool, SessionState::PendingTotp).await?;
    let got = authorize(&pool, &request("GET", &pending, None), now()).await?;
    assert_eq!(
        got,
        Authorization::Denied {
            reason: AuthzDenial::TotpIncomplete
        }
    );
    let issued = session_for(&pool, SessionState::Authenticated).await?;
    sqlx::query("update users set status = 'suspended' where id = $1::uuid")
        .bind(USER)
        .execute(&pool)
        .await?;
    let got = authorize(&pool, &request("GET", &issued, None), now()).await?;
    assert_eq!(
        got,
        Authorization::Denied {
            reason: AuthzDenial::AccountInactive
        }
    );
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn authorize_checks_csrf_on_mutations_only() -> Result<(), Failure> {
    let pool = pool().await?;
    let issued = session_for(&pool, SessionState::Authenticated).await?;
    let bad = Authorization::Denied {
        reason: AuthzDenial::CsrfInvalid,
    };
    assert_eq!(
        authorize(&pool, &request("POST", &issued, None), now()).await?,
        bad
    );
    let wrong = request("POST", &issued, Some("nope".to_owned()));
    assert_eq!(authorize(&pool, &wrong, now()).await?, bad);
    let right = request("POST", &issued, Some(issued.csrf_token.clone()));
    assert!(matches!(
        authorize(&pool, &right, now()).await?,
        Authorization::Allow { .. }
    ));
    assert!(matches!(
        authorize(&pool, &request("GET", &issued, None), now()).await?,
        Authorization::Allow { .. }
    ));
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn check_role_and_per_book_grants() -> Result<(), Failure> {
    let pool = pool().await?;
    let allow = CheckResult::Allow;
    assert_eq!(
        check(&pool, &ask("browse", Some(BOOK))?, now()).await?,
        allow
    );
    assert_eq!(
        check(&pool, &ask("manage_users", None)?, now()).await?,
        deny("no_scope")
    );
    assert_eq!(
        check(&pool, &ask("download", Some(BOOK))?, now()).await?,
        deny("no_scope")
    );
    grant(&pool, ("download", Some(BOOK)), 24).await?;
    assert_eq!(
        check(&pool, &ask("download", Some(BOOK))?, now()).await?,
        allow
    );
    let mut other = ask("download", Some(BOOK))?;
    other.book_id = Some(id("00000000-0000-7000-8000-0000000000b2")?);
    assert_eq!(check(&pool, &other, now()).await?, deny("no_scope"));
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn check_expired_grant_unknown_user_and_book_state() -> Result<(), Failure> {
    let pool = pool().await?;
    grant(&pool, ("download", Some(BOOK)), -1).await?;
    assert_eq!(
        check(&pool, &ask("download", Some(BOOK))?, now()).await?,
        deny("grant_expired")
    );
    let mut ghost = ask("browse", None)?;
    ghost.user_id = id("00000000-0000-7000-8000-0000000000ff")?;
    assert_eq!(check(&pool, &ghost, now()).await?, deny("account_inactive"));
    let mut hidden = ask("read", Some(BOOK))?;
    hidden.book_state = Some(BookState {
        published: false,
        deleted: false,
    });
    assert_eq!(
        check(&pool, &hidden, now()).await?,
        deny("book_not_published")
    );
    assert_eq!(
        check(&pool, &ask("nonsense", None)?, now()).await?,
        deny("no_scope")
    );
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn check_read_once_consumed() -> Result<(), Failure> {
    let pool = pool().await?;
    grant(&pool, ("read_once", Some(BOOK)), 24).await?;
    assert_eq!(
        check(&pool, &ask("read_once", Some(BOOK))?, now()).await?,
        CheckResult::Allow
    );
    sqlx::query(
        "insert into read_once_uses (user_id, book_id, ticket_id, consumed_at)
         values ($1::uuid, $2::uuid, gen_random_uuid(), now())",
    )
    .bind(USER)
    .bind(BOOK)
    .execute(&pool)
    .await?;
    assert_eq!(
        check(&pool, &ask("read_once", Some(BOOK))?, now()).await?,
        deny("read_once_consumed")
    );
    Ok(())
}

fn rand_seed() -> u128 {
    now().unix_millis().into()
}
