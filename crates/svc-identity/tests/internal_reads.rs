//! The internal reads against a real Postgres: ignored in a plain `cargo test`;
//! run by `cargo xtask check` (gate Q4).

use platform_config::{MapSource, PublicOrigin};
use platform_random::{OsRandom, to_hex};
use platform_testkit::TestDatabase;
use platform_time::Instant;
use sqlx::PgPool;
use svc_identity::MIGRATIONS;
use svc_identity::internal_reads::{
    MailContext, email_request, events_after, grant_version, user_info,
};
use svc_identity::vault::{Plain, VaultKey, seal};
use uuid::Uuid;

type Failure = Box<dyn std::error::Error>;

const USER: &str = "00000000-0000-7000-8000-00000000000a";
const NOW: i64 = 1_800_000_000;

fn user() -> Result<Uuid, Failure> {
    Ok(Uuid::parse_str(USER)?)
}

fn now() -> Result<Instant, Failure> {
    Instant::from_unix_seconds(NOW).ok_or_else(|| "bad instant".into())
}

async fn database() -> Result<PgPool, Failure> {
    let pool = TestDatabase::create(&MIGRATIONS).await?.pool;
    sqlx::query(
        "insert into users (id, email, display_name, language, status, role, grant_version, created_at, updated_at)
         values ($1::uuid, 'reader@example.org', 'Reader', 'bn', 'active', 'reader', 7, now(), now())",
    )
    .bind(USER)
    .execute(&pool)
    .await?;
    Ok(pool)
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn user_info_lists_addresses_in_order() -> Result<(), Failure> {
    let pool = database().await?;
    add_addresses(&pool).await?;
    let info = user_info(&pool, user()?).await?.ok_or("missing")?;
    assert_eq!(info.status, "active");
    assert_eq!(info.language, "bn");
    assert_eq!(info.kindle_addresses, ["a@kindle.com", "b@kindle.com"]);
    assert!(user_info(&pool, Uuid::nil()).await?.is_none());
    assert_eq!(grant_version(&pool, user()?).await?, Some(7));
    assert_eq!(grant_version(&pool, Uuid::nil()).await?, None);
    Ok(())
}

async fn add_addresses(pool: &PgPool) -> Result<(), Failure> {
    for (position, address) in [(1_i16, "b@kindle.com"), (0, "a@kindle.com")] {
        sqlx::query(
            "insert into kindle_addresses (user_id, position, address) values ($1, $2, $3)",
        )
        .bind(user()?)
        .bind(position)
        .bind(address)
        .execute(pool)
        .await?;
    }
    Ok(())
}

async fn add_events(pool: &PgPool) -> Result<(), Failure> {
    for index in 0..5_u128 {
        add_event(pool, index).await?;
    }
    Ok(())
}

async fn add_event(pool: &PgPool, index: u128) -> Result<(), Failure> {
    sqlx::query(
        "insert into events (id, type, v, subject_id, payload, at)
         values ($1, 'user.updated', 1, $2, '{\"n\": 1}'::jsonb, to_timestamp($3))",
    )
    .bind(Uuid::from_u128(index + 1))
    .bind(user()?)
    .bind(NOW)
    .execute(pool)
    .await?;
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn events_page_by_cursor() -> Result<(), Failure> {
    let pool = database().await?;
    add_events(&pool).await?;
    let first = events_after(&pool, 0, 2).await?;
    assert_eq!(first.events.len(), 2);
    assert_eq!(first.next, first.events.last().ok_or("empty")?.cursor);
    let head = first.events.first().ok_or("empty")?;
    assert_eq!(head.kind, "user.updated");
    assert_eq!(head.at, NOW);
    assert_eq!(head.payload.get("n"), Some(&serde_json::json!(1)));
    assert_eq!(head.subject_id.as_deref(), Some(USER));
    let rest = events_after(&pool, first.next, 500).await?;
    assert_eq!(rest.events.len(), 3);
    let empty = events_after(&pool, rest.next, 10).await?;
    assert_eq!(empty.events.len(), 0);
    assert_eq!(empty.next, rest.next);
    Ok(())
}

struct Mail<'a> {
    request_id: &'a str,
    state: &'a str,
    expires: i64,
}

async fn queue_link(pool: &PgPool, mail: &Mail<'_>) -> Result<(), Failure> {
    sqlx::query(
        "insert into links (id, user_id, purpose, token_hash, nonce, state, expires_at, request_id, created_at)
         values (gen_random_uuid(), $1, 'invite', $2, '\\x00', $3, to_timestamp($4), $5, to_timestamp($6))",
    )
    .bind(user()?)
    .bind(mail.request_id.as_bytes())
    .bind(mail.state)
    .bind(mail.expires)
    .bind(mail.request_id)
    .bind(NOW - 100)
    .execute(pool)
    .await?;
    Ok(())
}

async fn queue_mail(pool: &PgPool, mail: &Mail<'_>) -> Result<(), Failure> {
    queue_link(pool, mail).await?;
    let key = VaultKey::from_bytes(&[5; 32])?;
    let plain = Plain {
        owner: user()?,
        bytes: b"tok123",
    };
    let sealed = seal(&key, plain, &OsRandom)?;
    sqlx::query(
        "insert into email_requests (request_id, kind, user_id, language, link_ref, created_at)
         values ($1, 'invite', $2, 'en', $3, now())",
    )
    .bind(mail.request_id)
    .bind(user()?)
    .bind(to_hex(&sealed))
    .execute(pool)
    .await?;
    Ok(())
}

async fn read(
    pool: &PgPool,
    request_id: &str,
) -> Result<Option<svc_identity::internal_reads::EmailRequest>, Failure> {
    let key = VaultKey::from_bytes(&[5; 32])?;
    let origin = PublicOrigin::load(
        &MapSource::default().with("ELIBRARY_PUBLIC_ORIGIN", "https://lib.example"),
    )?;
    Ok(email_request(
        MailContext {
            pool,
            key: &key,
            origin: &origin,
        },
        request_id,
        now()?,
    )
    .await?)
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn email_request_is_read_once() -> Result<(), Failure> {
    let pool = database().await?;
    queue_mail(
        &pool,
        &Mail {
            request_id: "r1",
            state: "issued",
            expires: NOW + 1000,
        },
    )
    .await?;
    let mail = read(&pool, "r1").await?.ok_or("missing")?;
    assert_eq!(mail.kind, "invite");
    assert_eq!(mail.to, "reader@example.org");
    assert_eq!(mail.language, "en");
    assert_eq!(mail.link, "https://lib.example/accept-invite?token=tok123");
    assert!(read(&pool, "r1").await?.is_none());
    assert!(read(&pool, "unknown").await?.is_none());
    Ok(())
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn stale_links_are_not_mailed() -> Result<(), Failure> {
    let pool = database().await?;
    queue_mail(
        &pool,
        &Mail {
            request_id: "old",
            state: "superseded",
            expires: NOW + 1000,
        },
    )
    .await?;
    queue_mail(
        &pool,
        &Mail {
            request_id: "late",
            state: "issued",
            expires: NOW - 1,
        },
    )
    .await?;
    assert!(read(&pool, "old").await?.is_none());
    assert!(read(&pool, "late").await?.is_none());
    Ok(())
}
