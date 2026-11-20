//! The public read routes under `/api/catalog`: no session, metadata only (D-34). The gateway
//! rate-limits them; the handlers only read.

use axum::Router;
use axum::extract::{Path, RawQuery, State};
use axum::response::Response;
use axum::routing::get;
use contracts_http::Page;
use sqlx::PgPool;

use crate::reply::{Failure, public_json};
use crate::slug::SlugParam;
use crate::store::{self, Cursor, Lookup};

const DEFAULT_LIMIT: i64 = 24;
const MAX_LIMIT: i64 = 100;
const UNSUPPORTED: [&str; 9] = [
    "q",
    "writer",
    "translator",
    "editor",
    "publisher",
    "series",
    "category",
    "language",
    "snapshot",
];

/// The routes under `/api/catalog`, ready to merge into the public router.
pub fn routes(pool: PgPool) -> axum::Router {
    Router::new()
        .route("/api/catalog/books", get(list_route))
        .route("/api/catalog/books/{slug}", get(detail_route))
        .with_state(pool)
}

/// The list parameters this stage supports: `after`, `limit` and `sort=recent`. `q`, facets and
/// the other sorts arrive with search and are refused until then, so they never silently differ.
struct ListQuery {
    after: Option<Cursor>,
    limit: i64,
}

fn parse_list(raw: Option<&str>) -> Result<ListQuery, Failure> {
    let mut query = ListQuery {
        after: None,
        limit: DEFAULT_LIMIT,
    };
    for pair in raw
        .unwrap_or_default()
        .split('&')
        .filter(|pair| !pair.is_empty())
    {
        let (name, value) = pair.split_once('=').unwrap_or((pair, ""));
        apply(&mut query, name, value)?;
    }
    Ok(query)
}

fn apply(query: &mut ListQuery, name: &str, value: &str) -> Result<(), Failure> {
    match (name, value) {
        ("after", _) => query.after = Some(Cursor::parse(value).ok_or(Failure::Invalid("after"))?),
        ("limit", _) => query.limit = parse_limit(value)?,
        ("sort", "recent") => {}
        ("sort", _) => return Err(Failure::Invalid("sort")),
        (other, _) if UNSUPPORTED.contains(&other) => return Err(Failure::Invalid("q")),
        _ => {}
    }
    Ok(())
}

fn parse_limit(value: &str) -> Result<i64, Failure> {
    match value.parse::<i64>() {
        Ok(limit) if (1..=MAX_LIMIT).contains(&limit) => Ok(limit),
        Ok(_) | Err(_) => Err(Failure::Invalid("limit")),
    }
}

async fn list_route(
    State(pool): State<PgPool>,
    RawQuery(raw): RawQuery,
) -> Result<Response, Failure> {
    let query = parse_list(raw.as_deref())?;
    let page = store::list(&pool, query.after, query.limit).await?;
    Ok(public_json(&Page {
        items: page.cards,
        next: page.next.map(Cursor::encode),
    }))
}

async fn detail_route(
    State(pool): State<PgPool>,
    Path(slug): Path<String>,
) -> Result<Response, Failure> {
    let slug = SlugParam::parse(&slug).ok_or(Failure::NotFound)?;
    match store::by_slug(&pool, &slug).await? {
        Lookup::Found(detail) => Ok(public_json(&*detail)),
        Lookup::Moved(now) => Err(Failure::Moved(now)),
        Lookup::Missing => Err(Failure::NotFound),
    }
}

#[cfg(test)]
mod tests {
    use super::parse_list;

    #[test]
    fn defaults_and_accepted_parameters() {
        assert!(parse_list(None).is_ok_and(|query| query.limit == 24 && query.after.is_none()));
        assert!(parse_list(Some("limit=100&sort=recent")).is_ok_and(|query| query.limit == 100));
    }

    #[test]
    fn refuses_bad_limits_cursors_sorts_and_unsupported_search() {
        let bad = [
            "limit=0",
            "limit=101",
            "limit=x",
            "after=x",
            "sort=title",
            "q=abc",
            "writer=1",
        ];
        assert!(bad.iter().all(|raw| parse_list(Some(raw)).is_err()));
    }
}
