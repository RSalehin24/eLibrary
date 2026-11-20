//! The only module that touches SQL for the public reads. Visibility comes from the one
//! `visible_books` view (INV-CAT-002, 003); nothing here reads a source link.

use std::collections::HashMap;

use serde::Serialize;
use sqlx::{PgPool, Row, postgres::PgRow};
use uuid::Uuid;

use crate::slug::SlugParam;

/// One credit as the public sees it.
#[derive(Debug, Clone, Serialize)]
pub(crate) struct Contributor {
    pub(crate) id: Option<Uuid>,
    pub(crate) name: String,
    pub(crate) role: String,
}

#[derive(Debug, Clone, Serialize)]
pub(crate) struct SeriesRef {
    pub(crate) id: Uuid,
    pub(crate) name: String,
    pub(crate) ordinal: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub(crate) struct CategoryRef {
    pub(crate) id: Uuid,
    pub(crate) name: String,
}

/// The lists that hang off one version.
#[derive(Debug, Default)]
struct Extras {
    contributors: Vec<Contributor>,
    series: Vec<SeriesRef>,
    categories: Vec<CategoryRef>,
}

/// A book in a list.
#[derive(Debug, Serialize)]
pub(crate) struct Card {
    pub(crate) id: Uuid,
    pub(crate) slug: String,
    pub(crate) title: String,
    pub(crate) contributors: Vec<Contributor>,
    pub(crate) cover_url: String,
    pub(crate) summary: Option<String>,
    pub(crate) series: Vec<SeriesRef>,
    pub(crate) categories: Vec<CategoryRef>,
}

/// The metadata detail of one published book; never a source URL or preview text.
#[derive(Debug, Serialize)]
pub(crate) struct Detail {
    #[serde(flatten)]
    pub(crate) card: Card,
    pub(crate) subtitle: Option<String>,
    pub(crate) language: String,
    pub(crate) edition_label: Option<String>,
    pub(crate) publisher: Option<String>,
    pub(crate) first_published: Option<String>,
    pub(crate) has_preview: bool,
}

/// Where a keyset page resumes: after this publication time (microseconds) and book id.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) struct Cursor {
    pub(crate) micros: i64,
    pub(crate) book_id: Uuid,
}

impl Cursor {
    pub(crate) fn encode(self) -> String {
        format!("{}-{}", self.micros, self.book_id)
    }

    pub(crate) fn parse(text: &str) -> Option<Self> {
        let (micros, id) = text.split_once('-')?;
        Some(Self {
            micros: micros.parse().ok()?,
            book_id: Uuid::parse_str(id).ok()?,
        })
    }
}

/// A page of cards and where the next one starts.
pub(crate) struct CardPage {
    pub(crate) cards: Vec<Card>,
    pub(crate) next: Option<Cursor>,
}

/// The answer to a slug lookup.
pub(crate) enum Lookup {
    Found(Box<Detail>),
    /// The slug was the book's before; it now has this one.
    Moved(String),
    Missing,
}

const MICROS: &str = "(extract(epoch from published_at) * 1000000)::bigint";

fn cover_url(slug: &str) -> String {
    format!("/api/catalog/books/{slug}/cover")
}

/// Newest first. `limit` is validated by the caller; one extra row tells whether more follow.
pub(crate) async fn list(
    pool: &PgPool,
    after: Option<Cursor>,
    limit: i64,
) -> Result<CardPage, sqlx::Error> {
    let sql = format!(
        "select book_id, slug, version_id, title, summary, {MICROS} as micros from visible_books
         where $1::bigint is null
            or (published_at, book_id) < ('epoch'::timestamptz + $1::bigint * interval '1 microsecond', $2::uuid)
         order by published_at desc, book_id desc limit $3"
    );
    let rows = sqlx::query(sqlx::AssertSqlSafe(sql))
        .bind(after.map(|cursor| cursor.micros))
        .bind(after.map(|cursor| cursor.book_id))
        .bind(limit + 1)
        .fetch_all(pool)
        .await?;
    let more = i64::try_from(rows.len()).is_ok_and(|count| count > limit);
    let kept: Vec<&PgRow> = rows
        .iter()
        .take(usize::try_from(limit).unwrap_or(0))
        .collect();
    let next = match (more, kept.last()) {
        (true, Some(row)) => Some(Cursor {
            micros: row.try_get("micros")?,
            book_id: row.try_get("book_id")?,
        }),
        _ => None,
    };
    Ok(CardPage {
        cards: cards_of(pool, &kept).await?,
        next,
    })
}

async fn cards_of(pool: &PgPool, rows: &[&PgRow]) -> Result<Vec<Card>, sqlx::Error> {
    let versions = rows
        .iter()
        .map(|row| row.try_get("version_id"))
        .collect::<Result<Vec<Uuid>, _>>()?;
    let mut extras = extras_for(pool, &versions).await?;
    rows.iter()
        .map(|row| {
            let version: Uuid = row.try_get("version_id")?;
            card_of(row, extras.remove(&version).unwrap_or_default())
        })
        .collect()
}

fn card_of(row: &PgRow, extras: Extras) -> Result<Card, sqlx::Error> {
    let slug: String = row.try_get("slug")?;
    Ok(Card {
        id: row.try_get("book_id")?,
        cover_url: cover_url(&slug),
        slug,
        title: row.try_get("title")?,
        summary: row.try_get("summary")?,
        contributors: extras.contributors,
        series: extras.series,
        categories: extras.categories,
    })
}

/// The current slug's detail, or where an old slug now lives, or nothing.
pub(crate) async fn by_slug(pool: &PgPool, slug: &SlugParam) -> Result<Lookup, sqlx::Error> {
    let found = sqlx::query(
        "select v.*, (select display_name from agents where id = v.publisher_agent_id) as publisher,
                to_char(v.first_published, 'YYYY-MM-DD') as first_published_text,
                exists (select 1 from assets a where a.version_id = v.version_id and a.kind = 'preview') as has_preview
         from visible_books v where v.slug = $1",
    )
    .bind(slug.as_str())
    .fetch_optional(pool)
    .await?;
    match found {
        Some(row) => detail_of(pool, &row).await,
        None => moved(pool, slug).await,
    }
}

async fn detail_of(pool: &PgPool, row: &PgRow) -> Result<Lookup, sqlx::Error> {
    let version: Uuid = row.try_get("version_id")?;
    let mut extras = extras_for(pool, &[version]).await?;
    let card = card_of(row, extras.remove(&version).unwrap_or_default())?;
    Ok(Lookup::Found(Box::new(Detail {
        card,
        subtitle: row.try_get("subtitle")?,
        language: row.try_get("language")?,
        edition_label: row.try_get("edition_label")?,
        publisher: row.try_get("publisher")?,
        first_published: row.try_get("first_published_text")?,
        has_preview: row.try_get("has_preview")?,
    })))
}

/// An old slug of a book that is still visible under another slug (INV-CAT-005).
async fn moved(pool: &PgPool, slug: &SlugParam) -> Result<Lookup, sqlx::Error> {
    let current: Option<String> = sqlx::query_scalar(
        "select v.slug from book_slugs s join visible_books v on v.book_id = s.book_id where s.slug = $1",
    )
    .bind(slug.as_str())
    .fetch_optional(pool)
    .await?;
    Ok(match current {
        Some(now) if now != slug.as_str() => Lookup::Moved(now),
        Some(_) | None => Lookup::Missing,
    })
}

async fn extras_for(
    pool: &PgPool,
    versions: &[Uuid],
) -> Result<HashMap<Uuid, Extras>, sqlx::Error> {
    let mut grouped: HashMap<Uuid, Extras> = HashMap::new();
    for (version, credit) in contributors(pool, versions).await? {
        grouped
            .entry(version)
            .or_default()
            .contributors
            .push(credit);
    }
    for (version, series) in series(pool, versions).await? {
        grouped.entry(version).or_default().series.push(series);
    }
    for (version, category) in categories(pool, versions).await? {
        grouped
            .entry(version)
            .or_default()
            .categories
            .push(category);
    }
    Ok(grouped)
}

async fn contributors(
    pool: &PgPool,
    versions: &[Uuid],
) -> Result<Vec<(Uuid, Contributor)>, sqlx::Error> {
    let rows = sqlx::query(
        "select c.version_id, c.agent_id, coalesce(a.display_name, c.raw_name) as name, c.role
         from credits c left join agents a on a.id = c.agent_id
         where c.version_id = any($1) order by c.version_id, c.ordinal, c.role",
    )
    .bind(versions)
    .fetch_all(pool)
    .await?;
    rows.iter()
        .map(|row| {
            let credit = Contributor {
                id: row.try_get("agent_id")?,
                name: row.try_get("name")?,
                role: row.try_get("role")?,
            };
            Ok((row.try_get("version_id")?, credit))
        })
        .collect()
}

async fn series(pool: &PgPool, versions: &[Uuid]) -> Result<Vec<(Uuid, SeriesRef)>, sqlx::Error> {
    let rows = sqlx::query(
        "select vs.version_id, s.id, s.name, vs.ordinal::text as ordinal
         from version_series vs join series s on s.id = vs.series_id
         where vs.version_id = any($1) order by vs.version_id, s.name",
    )
    .bind(versions)
    .fetch_all(pool)
    .await?;
    rows.iter()
        .map(|row| {
            let series = SeriesRef {
                id: row.try_get("id")?,
                name: row.try_get("name")?,
                ordinal: row.try_get("ordinal")?,
            };
            Ok((row.try_get("version_id")?, series))
        })
        .collect()
}

async fn categories(
    pool: &PgPool,
    versions: &[Uuid],
) -> Result<Vec<(Uuid, CategoryRef)>, sqlx::Error> {
    let rows = sqlx::query(
        "select vc.version_id, c.id, c.name
         from version_categories vc join categories c on c.id = vc.category_id
         where vc.version_id = any($1) order by vc.version_id, c.name",
    )
    .bind(versions)
    .fetch_all(pool)
    .await?;
    rows.iter()
        .map(|row| {
            let category = CategoryRef {
                id: row.try_get("id")?,
                name: row.try_get("name")?,
            };
            Ok((row.try_get("version_id")?, category))
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::Cursor;
    use uuid::Uuid;

    #[test]
    fn a_cursor_survives_a_round_trip() {
        let cursor = Cursor {
            micros: 1_700_000_000_123_456,
            book_id: Uuid::from_u128(7),
        };
        assert_eq!(Cursor::parse(&cursor.encode()), Some(cursor));
    }

    #[test]
    fn a_malformed_cursor_is_refused() {
        assert_eq!(Cursor::parse(""), None);
        assert_eq!(Cursor::parse("12"), None);
        assert_eq!(
            Cursor::parse("x-00000000-0000-0000-0000-000000000000"),
            None
        );
        assert_eq!(Cursor::parse("12-not-a-uuid"), None);
    }
}
