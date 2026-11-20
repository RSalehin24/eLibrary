//! Reading tickets against a real Postgres: ignored in a plain `cargo test`;
//! run by `cargo xtask check` (gate Q4).

use domain_access::DenyReason;
use platform_testkit::TestDatabase;
use platform_time::Instant;
use sqlx::PgPool;
use svc_identity::MIGRATIONS;
use svc_identity::tickets::{
    MintOutcome, MintRequest, MintedTicket, TICKET_LIFETIME, TicketDenial, VerifyOutcome,
    VerifyRequest, mint, verify,
};
use uuid::Uuid;

type Failure = Box<dyn std::error::Error>;

const USER: &str = "00000000-0000-7000-8000-00000000000a";
const ADMIN: &str = "00000000-0000-7000-8000-00000000000b";
const BOOK: &str = "00000000-0000-7000-8000-0000000000b1";
const VERSION: &str = "00000000-0000-7000-8000-0000000000c1";

fn id(text: &str) -> Result<Uuid, Failure> {
    Ok(Uuid::parse_str(text)?)
}

fn now() -> Result<Instant, Failure> {
    Instant::from_unix_seconds(1_800_000_000).ok_or_else(|| "bad instant".into())
}

async fn setup(grants: &[&str]) -> Result<PgPool, Failure> {
    let pool = TestDatabase::create(&MIGRATIONS).await?.pool;
    for (user, email, role) in [
        (USER, "a@example.org", "reader"),
        (ADMIN, "b@example.org", "admin"),
    ] {
        sqlx::query(
            "insert into users (id, email, display_name, language, status, role, created_at, updated_at)
             values ($1::uuid, $2, 'U', 'en', 'active', $3, now(), now())",
        )
        .bind(user)
        .bind(email)
        .bind(role)
        .execute(&pool)
        .await?;
    }
    for scope in grants {
        grant(&pool, scope).await?;
    }
    Ok(pool)
}

async fn grant(pool: &PgPool, scope: &str) -> Result<(), Failure> {
    sqlx::query(
        "insert into grants (id, user_id, scope, granted_by, reason, created_at)
         values (gen_random_uuid(), $1::uuid, $2, $3::uuid, 'test', now())",
    )
    .bind(USER)
    .bind(scope)
    .bind(ADMIN)
    .execute(pool)
    .await?;
    Ok(())
}

async fn minted(pool: &PgPool) -> Result<MintedTicket, Failure> {
    let request = MintRequest {
        user_id: id(USER)?,
        book_id: id(BOOK)?,
        version_id: id(VERSION)?,
    };
    match mint(pool, request, now()?).await? {
        MintOutcome::Minted(ticket) => Ok(ticket),
        MintOutcome::Denied(reason) => Err(format!("denied: {reason:?}").into()),
    }
}

struct Attempt {
    redeem: bool,
    at: Instant,
}

async fn attempt(
    pool: &PgPool,
    ticket: &MintedTicket,
    how: Attempt,
) -> Result<VerifyOutcome, Failure> {
    let request = VerifyRequest {
        ticket_id: ticket.ticket_id,
        ticket: &ticket.ticket,
        book_id: id(BOOK)?,
        version_id: id(VERSION)?,
        redeem: how.redeem,
    };
    Ok(verify(pool, request, how.at).await?)
}

async fn check(
    pool: &PgPool,
    ticket: &MintedTicket,
    redeem: bool,
) -> Result<VerifyOutcome, Failure> {
    attempt(pool, ticket, Attempt { redeem, at: now()? }).await
}

fn valid() -> Result<VerifyOutcome, Failure> {
    Ok(VerifyOutcome::Valid { user_id: id(USER)? })
}

fn denied(denial: TicketDenial) -> VerifyOutcome {
    VerifyOutcome::Denied(denial)
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn mint_then_verify_succeeds_and_stores_only_a_hash() -> Result<(), Failure> {
    let pool = setup(&["read"]).await?;
    let ticket = minted(&pool).await?;
    assert_eq!(ticket.expires_at, now()?.unix_seconds() + 900);
    assert_eq!(check(&pool, &ticket, false).await?, valid()?);
    let stored: i64 = sqlx::query_scalar("select count(*) from tickets where secret_hash = $1")
        .bind(ticket.ticket.as_bytes())
        .fetch_one(&pool)
        .await?;
    assert_eq!(stored, 0);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn mint_for_a_suspended_user_is_denied() -> Result<(), Failure> {
    let pool = setup(&[]).await?;
    sqlx::query("update users set status = 'suspended' where id = $1::uuid")
        .bind(USER)
        .execute(&pool)
        .await?;
    let request = MintRequest {
        user_id: id(USER)?,
        book_id: id(BOOK)?,
        version_id: id(VERSION)?,
    };
    let outcome = mint(&pool, request, now()?).await?;
    assert_eq!(outcome, MintOutcome::Denied(DenyReason::AccountInactive));
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn wrong_token_or_ids_are_invalid() -> Result<(), Failure> {
    let pool = setup(&["read"]).await?;
    let ticket = minted(&pool).await?;
    let wrong = MintedTicket {
        ticket: "0".repeat(64),
        ..ticket.clone()
    };
    assert_eq!(
        check(&pool, &wrong, false).await?,
        denied(TicketDenial::Invalid)
    );
    let unknown = MintedTicket {
        ticket_id: Uuid::nil(),
        ..ticket
    };
    assert_eq!(
        check(&pool, &unknown, false).await?,
        denied(TicketDenial::Invalid)
    );
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn expired_ticket_is_rejected() -> Result<(), Failure> {
    let pool = setup(&["read"]).await?;
    let ticket = minted(&pool).await?;
    let later = now()?.checked_add(TICKET_LIFETIME).ok_or("range")?;
    assert_eq!(
        attempt(
            &pool,
            &ticket,
            Attempt {
                redeem: false,
                at: later
            }
        )
        .await?,
        denied(TicketDenial::Expired)
    );
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn revoked_read_once_grant_after_mint_is_re_decided() -> Result<(), Failure> {
    let pool = setup(&["read_once"]).await?;
    let first = minted(&pool).await?;
    let second = minted(&pool).await?;
    assert_eq!(check(&pool, &first, true).await?, valid()?);
    sqlx::query("update grants set active = false where user_id = $1::uuid")
        .bind(USER)
        .execute(&pool)
        .await?;
    sqlx::query("update users set grant_version = grant_version + 1 where id = $1::uuid")
        .bind(USER)
        .execute(&pool)
        .await?;
    // The grant is gone, so the role's plain read decides and the spent use no longer binds.
    assert_eq!(check(&pool, &second, true).await?, valid()?);
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn suspended_user_is_rejected() -> Result<(), Failure> {
    let pool = setup(&["read"]).await?;
    let ticket = minted(&pool).await?;
    sqlx::query("update users set status = 'suspended' where id = $1::uuid")
        .bind(USER)
        .execute(&pool)
        .await?;
    assert_eq!(
        check(&pool, &ticket, false).await?,
        denied(TicketDenial::Invalid)
    );
    Ok(())
}

async fn uses(pool: &PgPool) -> Result<i64, Failure> {
    Ok(sqlx::query_scalar("select count(*) from read_once_uses")
        .fetch_one(pool)
        .await?)
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn read_once_redeem_is_idempotent_per_ticket_and_consumed_for_another() -> Result<(), Failure>
{
    let pool = setup(&["read_once"]).await?;
    let first = minted(&pool).await?;
    let second = minted(&pool).await?;
    assert_eq!(check(&pool, &first, false).await?, valid()?);
    assert_eq!(uses(&pool).await?, 0);
    assert_eq!(check(&pool, &first, true).await?, valid()?);
    assert_eq!(check(&pool, &first, true).await?, valid()?);
    assert_eq!(uses(&pool).await?, 1);
    assert_eq!(
        check(&pool, &second, true).await?,
        denied(TicketDenial::ReadOnceConsumed)
    );
    let request = MintRequest {
        user_id: id(USER)?,
        book_id: id(BOOK)?,
        version_id: id(VERSION)?,
    };
    let again = mint(&pool, request, now()?).await?;
    assert!(matches!(again, MintOutcome::Denied(_)));
    Ok(())
}
