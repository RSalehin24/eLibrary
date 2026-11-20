//! Administration, read side: the user list and one user's detail (`manage_users`).

use std::collections::HashMap;

use serde::Serialize;
use sqlx::{PgPool, Row};
use uuid::Uuid;

/// Rows per page when the caller gives no limit, and the most it may ask for.
// why: the value is provisional in the limits table (100 rows, O-7).
const DEFAULT_LIMIT: i64 = 100;
const STATUSES: [&str; 4] = ["invited", "active", "suspended", "disabled"];
const ROLES: [&str; 3] = ["reader", "operator", "admin"];

#[derive(Serialize)]
pub(crate) struct UserRow {
    #[serde(skip)]
    key: Uuid,
    id: String,
    email: String,
    display_name: String,
    language: String,
    role: String,
    status: String,
    created_at: i64,
}

#[derive(Serialize)]
pub(crate) struct UserDetail {
    #[serde(flatten)]
    user: UserRow,
    revision: i64,
    active_grants: i64,
    grant_scopes: Vec<String>,
}

#[derive(Serialize)]
pub(crate) struct UserPage {
    items: Vec<UserRow>,
    next: Option<String>,
}

/// A checked list request.
pub(crate) struct Listing {
    pattern: Option<String>,
    status: Option<String>,
    role: Option<String>,
    after: Option<Uuid>,
    limit: i64,
}

/// `LIKE` pattern matching the text anywhere, with the wildcards in the text escaped.
fn contains_pattern(text: &str) -> String {
    let escaped = text
        .replace('\\', "\\\\")
        .replace('%', "\\%")
        .replace('_', "\\_");
    format!("%{escaped}%")
}

fn one_of(
    value: Option<&String>,
    allowed: &[&str],
    field: &'static str,
) -> Result<Option<String>, &'static str> {
    match value {
        None => Ok(None),
        Some(text) if allowed.contains(&text.as_str()) => Ok(Some(text.clone())),
        Some(_) => Err(field),
    }
}

/// The first bad parameter's name, or the checked request.
pub(crate) fn listing(params: &HashMap<String, String>) -> Result<Listing, &'static str> {
    let status = one_of(params.get("status"), &STATUSES, "status")?;
    let role = one_of(params.get("role"), &ROLES, "role")?;
    let after = params
        .get("after")
        .map(|token| Uuid::parse_str(token).map_err(|_| "after"))
        .transpose()?;
    let limit = match params.get("limit") {
        None => DEFAULT_LIMIT,
        Some(text) => text
            .parse::<i64>()
            .ok()
            .filter(|value| (1..=DEFAULT_LIMIT).contains(value))
            .ok_or("limit")?,
    };
    let pattern = params
        .get("q")
        .filter(|text| !text.trim().is_empty())
        .map(|text| contains_pattern(text.trim()));
    Ok(Listing {
        pattern,
        status,
        role,
        after,
        limit,
    })
}

fn row_of(row: &sqlx::postgres::PgRow) -> Result<UserRow, sqlx::Error> {
    let key: Uuid = row.try_get("id")?;
    Ok(UserRow {
        key,
        id: contracts_ids::UserId::from_uuid(key).to_string(),
        email: row.try_get("email")?,
        display_name: row.try_get("display_name")?,
        language: row.try_get("language")?,
        role: row.try_get("role")?,
        status: row.try_get("status")?,
        created_at: row.try_get("created_at")?,
    })
}

pub(crate) async fn list(pool: &PgPool, request: Listing) -> Result<UserPage, sqlx::Error> {
    let rows = sqlx::query(
        "select id, email, display_name, language, role, status,
                extract(epoch from created_at)::bigint as created_at
         from users
         where ($1::text is null or email ilike $1 escape '\\' or display_name ilike $1 escape '\\')
           and ($2::text is null or status = $2)
           and ($3::text is null or role = $3)
           and ($4::uuid is null or id > $4)
         order by id limit $5",
    )
    .bind(request.pattern)
    .bind(request.status)
    .bind(request.role)
    .bind(request.after)
    .bind(request.limit + 1)
    .fetch_all(pool)
    .await?;
    let mut items = rows.iter().map(row_of).collect::<Result<Vec<_>, _>>()?;
    let more = i64::try_from(items.len()).is_ok_and(|count| count > request.limit);
    if more {
        items.pop();
    }
    let next = more
        .then(|| items.last().map(|row| row.key.to_string()))
        .flatten();
    Ok(UserPage { items, next })
}

pub(crate) async fn detail(pool: &PgPool, id: Uuid) -> Result<Option<UserDetail>, sqlx::Error> {
    let row = sqlx::query(
        "select id, email, display_name, language, role, status, revision,
                extract(epoch from created_at)::bigint as created_at
         from users where id = $1",
    )
    .bind(id)
    .fetch_optional(pool)
    .await?;
    let Some(row) = row else { return Ok(None) };
    let scopes: Vec<String> = sqlx::query_scalar(
        "select scope from grants where user_id = $1 and active
           and (expires_at is null or expires_at > now()) order by scope",
    )
    .bind(id)
    .fetch_all(pool)
    .await?;
    Ok(Some(UserDetail {
        user: row_of(&row)?,
        revision: row.try_get("revision")?,
        active_grants: i64::try_from(scopes.len()).unwrap_or(i64::MAX),
        grant_scopes: scopes,
    }))
}
