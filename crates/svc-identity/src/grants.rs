//! Explicit grants of a scope to a user, for one book or globally (REQ-IDN-011, 012, 017).
//! Every change locks the user, raises their grant version and writes one `grant.changed`
//! event and an audit row in the same transaction.

use contracts_http::CommonErrorCode;
use contracts_ids::{BookId, UserId};
use platform_random::{OsRandom, uuid_v7};
use platform_time::Instant;
use serde::Serialize;
use sqlx::{PgConnection, PgPool, Row};
use uuid::Uuid;

use crate::admin_change::{
    ChangeError, Outgoing, Request, audit_change, bump_grant_version, emit_with,
};

const SCOPES: [&str; 9] = [
    "browse",
    "preview",
    "read",
    "read_once",
    "download",
    "kindle",
    "operate",
    "manage_catalog",
    "manage_users",
];
const BOOK_SCOPES: [&str; 5] = ["preview", "read", "read_once", "download", "kindle"];
const REASON_MAX_CHARS: usize = 500;

/// Why a grant change was refused.
pub(crate) enum Refusal {
    /// A request field is wrong.
    Invalid(&'static str),
    /// The same user, scope and book already have an active grant.
    Duplicate,
    Code(CommonErrorCode),
}

pub(crate) enum GrantError {
    Failed(ChangeError),
    Refused(Refusal),
}

fn from_sqlx(error: sqlx::Error) -> GrantError {
    let duplicate = error
        .as_database_error()
        .is_some_and(|db| db.code().as_deref() == Some("23505"));
    if duplicate {
        GrantError::Refused(Refusal::Duplicate)
    } else {
        GrantError::Failed(ChangeError::Database(error))
    }
}

impl From<sqlx::Error> for GrantError {
    fn from(error: sqlx::Error) -> Self {
        from_sqlx(error)
    }
}

impl From<ChangeError> for GrantError {
    fn from(error: ChangeError) -> Self {
        Self::Failed(error)
    }
}

/// One grant to create, as typed.
#[derive(Clone)]
pub(crate) struct Spec {
    pub scope: String,
    pub book_id: Option<String>,
    pub expires_at: Option<i64>,
}

/// A checked grant to create.
struct Checked {
    scope: String,
    book: Option<Uuid>,
    expires: Option<Instant>,
}

/// The first wrong field of a grant spec.
fn check(spec: &Spec, now: Instant) -> Result<Checked, &'static str> {
    if !SCOPES.contains(&spec.scope.as_str()) {
        return Err("scope");
    }
    let book = spec
        .book_id
        .as_deref()
        .map(|text| {
            text.parse::<BookId>()
                .map(|id| id.as_uuid())
                .map_err(|_| "book_id")
        })
        .transpose()?;
    if book.is_some() && !BOOK_SCOPES.contains(&spec.scope.as_str()) {
        return Err("book_id");
    }
    let expires = spec
        .expires_at
        .map(|seconds| {
            Instant::from_unix_seconds(seconds)
                .filter(|at| *at > now)
                .ok_or("expires_at")
        })
        .transpose()?;
    Ok(Checked {
        scope: spec.scope.clone(),
        book,
        expires,
    })
}

/// The reason text, trimmed, 1 to 500 characters.
pub(crate) fn check_reason(reason: &str) -> Result<&str, &'static str> {
    let reason = reason.trim();
    let length = reason.chars().count();
    (1..=REASON_MAX_CHARS)
        .contains(&length)
        .then_some(reason)
        .ok_or("reason")
}

/// Who grants to whom, why, and when.
#[derive(Clone, Copy)]
pub(crate) struct Change<'a> {
    pub pool: &'a PgPool,
    pub now: Instant,
    pub actor: Uuid,
    pub user: Uuid,
    pub reason: &'a str,
}

impl Change<'_> {
    fn request(&self) -> Request<'_> {
        Request {
            pool: self.pool,
            now: self.now,
            actor: self.actor,
            target: self.user,
        }
    }
}

#[derive(Serialize)]
pub(crate) struct GrantRow {
    id: String,
    user_id: String,
    scope: String,
    book_id: Option<String>,
    expires_at: Option<i64>,
    active: bool,
    reason: String,
    revision: i64,
    created_at: i64,
}

/// A grant select with the given tail (`where ...`), as one compile-time SQL string.
macro_rules! grant_select {
    ($tail:literal) => {
        concat!(
            "select id, user_id, scope, book_id, active, reason, revision,
                extract(epoch from expires_at)::bigint as expires_at,
                extract(epoch from created_at)::bigint as created_at from grants ",
            $tail
        )
    };
}

fn row_of(row: &sqlx::postgres::PgRow) -> Result<GrantRow, sqlx::Error> {
    let book: Option<Uuid> = row.try_get("book_id")?;
    Ok(GrantRow {
        id: row.try_get::<Uuid, _>("id")?.to_string(),
        user_id: UserId::from_uuid(row.try_get("user_id")?).to_string(),
        scope: row.try_get("scope")?,
        book_id: book.map(|id| BookId::from_uuid(id).to_string()),
        expires_at: row.try_get("expires_at")?,
        active: row.try_get("active")?,
        reason: row.try_get("reason")?,
        revision: row.try_get("revision")?,
        created_at: row.try_get("created_at")?,
    })
}

/// Locks the user row; false when there is no such user or it is the actor.
async fn lock_user(
    connection: &mut PgConnection,
    change: &Change<'_>,
) -> Result<Result<(), CommonErrorCode>, sqlx::Error> {
    let found: Option<Uuid> = sqlx::query_scalar("select id from users where id = $1 for update")
        .bind(change.user)
        .fetch_optional(connection)
        .await?;
    Ok(match found {
        None => Err(CommonErrorCode::NotFound),
        Some(_) if change.actor == change.user => Err(CommonErrorCode::Forbidden),
        Some(_) => Ok(()),
    })
}

async fn insert(
    connection: &mut PgConnection,
    change: &Change<'_>,
    grant: &Checked,
) -> Result<Uuid, GrantError> {
    let id = uuid_v7(change.now.unix_millis(), &OsRandom).map_err(ChangeError::from)?;
    sqlx::query(
        "insert into grants (id, user_id, scope, book_id, expires_at, granted_by, reason, created_at)
         values ($1, $2, $3, $4, $5, $6, $7, $8)",
    )
    .bind(id)
    .bind(change.user)
    .bind(&grant.scope)
    .bind(grant.book)
    .bind(grant.expires.map(|at| at.to_offset_date_time()))
    .bind(change.actor)
    .bind(change.reason)
    .bind(change.now.to_offset_date_time())
    .execute(connection)
    .await?;
    Ok(id)
}

/// Raises the version, emits `grant.changed` and audits; `detail` names what changed.
async fn announce(
    connection: &mut PgConnection,
    change: &Change<'_>,
    detail: (&str, Option<&Checked>),
) -> Result<(), GrantError> {
    let (action, grant) = detail;
    let request = change.request();
    let version = bump_grant_version(connection, request).await?;
    let mut payload = serde_json::Map::new();
    payload.insert(
        "user_id".into(),
        UserId::from_uuid(change.user).to_string().into(),
    );
    payload.insert("grant_version".into(), version.into());
    if let Some(grant) = grant {
        let book = grant.book.map(|id| BookId::from_uuid(id).to_string());
        payload.insert("scope".into(), grant.scope.clone().into());
        payload.insert("book_id".into(), book.into());
    }
    let event = Outgoing {
        kind: "grant.changed",
        payload: payload.into(),
    };
    emit_with(connection, request, event).await?;
    audit_change(connection, request, action).await?;
    Ok(())
}

/// Creates one grant.
pub(crate) async fn create(change: Change<'_>, spec: &Spec) -> Result<GrantRow, GrantError> {
    let grant =
        check(spec, change.now).map_err(|field| GrantError::Refused(Refusal::Invalid(field)))?;
    let mut transaction = change.pool.begin().await?;
    if let Err(code) = lock_user(&mut transaction, &change).await? {
        return Err(GrantError::Refused(Refusal::Code(code)));
    }
    let id = insert(&mut transaction, &change, &grant).await?;
    announce(&mut transaction, &change, ("grant_created", Some(&grant))).await?;
    let row = sqlx::query(grant_select!("where id = $1"))
        .bind(id)
        .fetch_one(&mut *transaction)
        .await?;
    transaction.commit().await?;
    Ok(row_of(&row)?)
}

/// A grant's current state, locked.
struct Held {
    user: Uuid,
    revision: i64,
    active: bool,
}

async fn lock_grant(connection: &mut PgConnection, id: Uuid) -> Result<Option<Held>, sqlx::Error> {
    let row = sqlx::query("select user_id, revision, active from grants where id = $1 for update")
        .bind(id)
        .fetch_optional(connection)
        .await?;
    row.map(|row| {
        Ok(Held {
            user: row.try_get("user_id")?,
            revision: row.try_get("revision")?,
            active: row.try_get("active")?,
        })
    })
    .transpose()
}

/// What PATCH does to the expiry.
#[derive(Clone, Copy, Default)]
pub(crate) enum Expiry {
    #[default]
    Keep,
    Clear,
    Set(i64),
}

/// What PATCH may change; `None` leaves a field alone.
#[derive(Clone, Copy)]
pub(crate) struct Edit {
    pub expires_at: Expiry,
    pub active: Option<bool>,
}

/// The grant being edited and the revision the caller saw.
#[derive(Clone, Copy)]
pub(crate) struct Target {
    pub grant: Uuid,
    pub revision: i64,
}

fn refuse<T>(code: CommonErrorCode) -> Result<T, GrantError> {
    Err(GrantError::Refused(Refusal::Code(code)))
}

/// Locks the grant and its user and checks the revision; returns the change for that user.
async fn lock_for_edit<'a>(
    connection: &mut PgConnection,
    change: Change<'a>,
    target: Target,
) -> Result<Change<'a>, GrantError> {
    let Some(held) = lock_grant(connection, target.grant).await? else {
        return refuse(CommonErrorCode::NotFound);
    };
    let change = Change {
        user: held.user,
        ..change
    };
    if let Err(code) = lock_user(connection, &change).await? {
        return refuse(code);
    }
    if held.revision != target.revision {
        return refuse(CommonErrorCode::StaleRevision);
    }
    Ok(change)
}

/// The expiry instant an edit sets, if any; it must lie in the future.
fn new_expiry(expiry: Expiry, now: Instant) -> Result<Option<Instant>, GrantError> {
    match expiry {
        Expiry::Set(seconds) => Instant::from_unix_seconds(seconds)
            .filter(|at| *at > now)
            .map(Some)
            .ok_or(GrantError::Refused(Refusal::Invalid("expires_at"))),
        Expiry::Keep | Expiry::Clear => Ok(None),
    }
}

/// Edits expiry or the active flag of one grant (`If-Match` revision).
pub(crate) async fn edit(
    change: Change<'_>,
    target: Target,
    edit: Edit,
) -> Result<GrantRow, GrantError> {
    let expires = new_expiry(edit.expires_at, change.now)?;
    let mut transaction = change.pool.begin().await?;
    let change = lock_for_edit(&mut transaction, change, target).await?;
    sqlx::query(
        "update grants set revision = revision + 1,
                active = coalesce($2, active),
                expires_at = case when $3 then $4 else expires_at end
         where id = $1",
    )
    .bind(target.grant)
    .bind(edit.active)
    .bind(!matches!(edit.expires_at, Expiry::Keep))
    .bind(expires.map(|at| at.to_offset_date_time()))
    .execute(&mut *transaction)
    .await?;
    announce(&mut transaction, &change, ("grant_edited", None)).await?;
    let row = sqlx::query(grant_select!("where id = $1"))
        .bind(target.grant)
        .fetch_one(&mut *transaction)
        .await?;
    transaction.commit().await?;
    Ok(row_of(&row)?)
}

/// Revokes a grant (active false); revoking a revoked grant changes nothing.
pub(crate) async fn revoke(change: Change<'_>, grant: Uuid) -> Result<(), GrantError> {
    let mut transaction = change.pool.begin().await?;
    let Some(held) = lock_grant(&mut transaction, grant).await? else {
        return refuse(CommonErrorCode::NotFound);
    };
    let change = Change {
        user: held.user,
        ..change
    };
    if let Err(code) = lock_user(&mut transaction, &change).await? {
        return refuse(code);
    }
    if held.active {
        revoke_locked(&mut transaction, grant).await?;
        announce(&mut transaction, &change, ("grant_revoked", None)).await?;
    }
    transaction.commit().await?;
    Ok(())
}

async fn revoke_locked(connection: &mut PgConnection, grant: Uuid) -> Result<(), sqlx::Error> {
    sqlx::query("update grants set active = false, revision = revision + 1 where id = $1")
        .bind(grant)
        .execute(connection)
        .await
        .map(|_| ())
}

/// Several grants and revocations for one user, all or nothing, with one event.
pub(crate) async fn batch(
    change: Change<'_>,
    grants: &[Spec],
    revoke: &[Uuid],
) -> Result<Vec<GrantRow>, GrantError> {
    let checked = grants
        .iter()
        .map(|spec| check(spec, change.now))
        .collect::<Result<Vec<_>, _>>()
        .map_err(|field| GrantError::Refused(Refusal::Invalid(field)))?;
    if checked.is_empty() && revoke.is_empty() {
        return Err(GrantError::Refused(Refusal::Invalid("grant")));
    }
    let mut transaction = change.pool.begin().await?;
    if let Err(code) = lock_user(&mut transaction, &change).await? {
        return refuse(code);
    }
    for id in revoke {
        revoke_one(&mut transaction, &change, *id).await?;
    }
    let mut created = Vec::new();
    for grant in &checked {
        created.push(insert(&mut transaction, &change, grant).await?);
    }
    announce(&mut transaction, &change, ("grant_batch", None)).await?;
    let rows = sqlx::query(grant_select!("where id = any($1) order by id"))
        .bind(&created)
        .fetch_all(&mut *transaction)
        .await?;
    transaction.commit().await?;
    Ok(rows.iter().map(row_of).collect::<Result<_, _>>()?)
}

/// Revokes a grant that must belong to the batch's user.
async fn revoke_one(
    connection: &mut PgConnection,
    change: &Change<'_>,
    id: Uuid,
) -> Result<(), GrantError> {
    match lock_grant(connection, id).await? {
        Some(held) if held.user == change.user => Ok(revoke_locked(connection, id).await?),
        _ => refuse(CommonErrorCode::NotFound),
    }
}

/// A checked list request.
pub(crate) struct Listing {
    pub user: Option<Uuid>,
    pub scope: Option<String>,
    pub book: Option<Uuid>,
    pub after: Option<Uuid>,
    pub limit: i64,
}

pub(crate) async fn list(
    pool: &PgPool,
    request: Listing,
) -> Result<(Vec<GrantRow>, Option<String>), sqlx::Error> {
    let rows = sqlx::query(grant_select!(
        "where ($1::uuid is null or user_id = $1) and ($2::text is null or scope = $2)
           and ($3::uuid is null or book_id = $3) and ($4::uuid is null or id > $4)
         order by id limit $5"
    ))
    .bind(request.user)
    .bind(request.scope)
    .bind(request.book)
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
        .then(|| items.last().map(|row| row.id.clone()))
        .flatten();
    Ok((items, next))
}
