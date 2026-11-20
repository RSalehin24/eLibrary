//! Reading the insert-only audit log (`manage_users`, D-84): newest first, filtered by actor,
//! subject, action and period, paged by row id.

use std::collections::HashMap;

use serde::Serialize;
use sqlx::{PgPool, Row};

const DEFAULT_LIMIT: i64 = 100;

#[derive(Serialize)]
pub(crate) struct AuditRow {
    id: i64,
    at: i64,
    actor: String,
    subject: Option<String>,
    action: String,
    detail: serde_json::Value,
    request_id: Option<String>,
    address: Option<String>,
}

#[derive(Serialize)]
pub(crate) struct AuditPage {
    items: Vec<AuditRow>,
    next: Option<String>,
}

/// A checked read request.
pub(crate) struct Query {
    actor: Option<String>,
    subject: Option<String>,
    action: Option<String>,
    from: Option<i64>,
    to: Option<i64>,
    after: Option<i64>,
    limit: i64,
}

fn number(
    params: &HashMap<String, String>,
    name: &'static str,
) -> Result<Option<i64>, &'static str> {
    params
        .get(name)
        .map(|text| text.parse::<i64>().map_err(|_| name))
        .transpose()
}

/// The first bad parameter's name, or the checked request.
pub(crate) fn query(params: &HashMap<String, String>) -> Result<Query, &'static str> {
    let limit = number(params, "limit")?.unwrap_or(DEFAULT_LIMIT);
    if !(1..=DEFAULT_LIMIT).contains(&limit) {
        return Err("limit");
    }
    Ok(Query {
        actor: params.get("actor").cloned(),
        subject: params.get("subject").cloned(),
        action: params.get("action").cloned(),
        from: number(params, "from")?,
        to: number(params, "to")?,
        after: number(params, "after")?,
        limit,
    })
}

fn row_of(row: &sqlx::postgres::PgRow) -> Result<AuditRow, sqlx::Error> {
    Ok(AuditRow {
        id: row.try_get("id")?,
        at: row.try_get("at")?,
        actor: row.try_get("actor")?,
        subject: row.try_get("subject")?,
        action: row.try_get("action")?,
        detail: row.try_get("detail")?,
        request_id: row.try_get("request_id")?,
        address: row.try_get("address")?,
    })
}

pub(crate) async fn read(pool: &PgPool, request: Query) -> Result<AuditPage, sqlx::Error> {
    let rows = sqlx::query(
        "select id, extract(epoch from at)::bigint as at, actor, subject, action, detail, request_id, address
         from audit_log
         where ($1::text is null or actor = $1) and ($2::text is null or subject = $2)
           and ($3::text is null or action = $3)
           and ($4::bigint is null or at >= to_timestamp($4))
           and ($5::bigint is null or at < to_timestamp($5))
           and ($6::bigint is null or id < $6)
         order by id desc limit $7",
    )
    .bind(request.actor)
    .bind(request.subject)
    .bind(request.action)
    .bind(request.from)
    .bind(request.to)
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
        .then(|| items.last().map(|row| row.id.to_string()))
        .flatten();
    Ok(AuditPage { items, next })
}
