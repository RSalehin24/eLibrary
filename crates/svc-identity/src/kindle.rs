//! The own Kindle delivery addresses: at most five, each a validated `KindleEmail`
//! (REQ-IDN-028); the routes need the `kindle` scope.

use std::collections::HashSet;

use domain_credentials::KindleEmail;
use serde::{Deserialize, Serialize};
use sqlx::PgPool;
use uuid::Uuid;

/// Most addresses one account may hold.
pub(crate) const MAX_ADDRESSES: usize = 5;

#[derive(Serialize)]
pub(crate) struct Addresses {
    addresses: Vec<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Replacement {
    addresses: Vec<String>,
}

/// Why a replacement was refused.
pub(crate) enum Refusal {
    TooMany,
    Invalid,
}

/// The parsed list, with no address twice.
pub(crate) fn validate(replacement: &Replacement) -> Result<Vec<KindleEmail>, Refusal> {
    if replacement.addresses.len() > MAX_ADDRESSES {
        return Err(Refusal::TooMany);
    }
    let parsed = replacement
        .addresses
        .iter()
        .map(|raw| KindleEmail::parse(raw))
        .collect::<Result<Vec<_>, _>>()
        .map_err(|_| Refusal::Invalid)?;
    let distinct: HashSet<&KindleEmail> = parsed.iter().collect();
    if distinct.len() == parsed.len() {
        Ok(parsed)
    } else {
        Err(Refusal::Invalid)
    }
}

impl Addresses {
    pub(crate) fn into_inner(self) -> Vec<String> {
        self.addresses
    }
}

pub(crate) async fn list(pool: &PgPool, user: Uuid) -> Result<Addresses, sqlx::Error> {
    let addresses = sqlx::query_scalar(
        "select address from kindle_addresses where user_id = $1 order by position",
    )
    .bind(user)
    .fetch_all(pool)
    .await?;
    Ok(Addresses { addresses })
}

/// Replaces the whole list in one transaction.
pub(crate) async fn replace(
    pool: &PgPool,
    user: Uuid,
    addresses: &[KindleEmail],
) -> Result<(), sqlx::Error> {
    let mut transaction = pool.begin().await?;
    sqlx::query("delete from kindle_addresses where user_id = $1")
        .bind(user)
        .execute(&mut *transaction)
        .await?;
    for (position, address) in (0_i16..).zip(addresses) {
        sqlx::query(
            "insert into kindle_addresses (user_id, position, address) values ($1, $2, $3)",
        )
        .bind(user)
        .bind(position)
        .bind(address.as_str())
        .execute(&mut *transaction)
        .await?;
    }
    transaction.commit().await
}
