//! The user's own identity data as one JSON document (REQ-IDN-031, D-55): the profile, Kindle
//! addresses, TOTP state and grants. Hashes, secrets and sessions are not part of it.

use serde::Serialize;
use sqlx::{PgPool, Row};
use uuid::Uuid;

use crate::kindle;
use crate::me::{self, Me};
use crate::totp_manage;

#[derive(Serialize)]
struct GrantRecord {
    scope: String,
    book_id: Option<String>,
    expires_at: Option<i64>,
    active: bool,
    created_at: i64,
}

#[derive(Serialize)]
pub(crate) struct Export {
    profile: Me,
    created_at: i64,
    kindle_addresses: Vec<String>,
    totp: &'static str,
    grants: Vec<GrantRecord>,
}

/// `None` when the account is not active any more.
pub(crate) async fn collect(pool: &PgPool, user: Uuid) -> Result<Option<Export>, sqlx::Error> {
    let Some(profile) = me::find(pool, user).await? else {
        return Ok(None);
    };
    let created_at: i64 = sqlx::query_scalar(
        "select extract(epoch from created_at)::bigint from users where id = $1",
    )
    .bind(user)
    .fetch_one(pool)
    .await?;
    Ok(Some(Export {
        profile,
        created_at,
        kindle_addresses: kindle::list(pool, user).await?.into_inner(),
        totp: totp_manage::status(pool, user).await?,
        grants: grants(pool, user).await?,
    }))
}

async fn grants(pool: &PgPool, user: Uuid) -> Result<Vec<GrantRecord>, sqlx::Error> {
    let rows = sqlx::query(
        "select scope, book_id, extract(epoch from expires_at)::bigint as expires_at, active,
                extract(epoch from created_at)::bigint as created_at
         from grants where user_id = $1 order by created_at, id",
    )
    .bind(user)
    .fetch_all(pool)
    .await?;
    rows.iter()
        .map(|row| {
            let book: Option<Uuid> = row.try_get("book_id")?;
            Ok(GrantRecord {
                scope: row.try_get("scope")?,
                book_id: book.map(|id| contracts_ids::BookId::from_uuid(id).to_string()),
                expires_at: row.try_get("expires_at")?,
                active: row.try_get("active")?,
                created_at: row.try_get("created_at")?,
            })
        })
        .collect()
}
