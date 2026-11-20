//! Administration, write side: account status and role changes. Each change locks the target
//! (and the active admins when one could be the last), bumps the grant version, records an
//! outbox event and an audit row in the same transaction.

use contracts_http::CommonErrorCode;
use contracts_ids::UserId;
use platform_random::{OsRandom, RandomError, uuid_v7};
use platform_time::Instant;
use sqlx::{PgConnection, PgPool, Row};
use thiserror::Error;
use uuid::Uuid;

use crate::audit::{self, AuditEntry};

#[derive(Debug, Error)]
pub(crate) enum ChangeError {
    #[error("database: {0}")]
    Database(#[from] sqlx::Error),
    #[error("randomness: {0}")]
    Random(#[from] RandomError),
}

/// Who changes what, and when.
#[derive(Clone, Copy)]
pub(crate) struct Request<'a> {
    pub pool: &'a PgPool,
    pub now: Instant,
    pub actor: Uuid,
    pub target: Uuid,
}

/// What happened, apart from infrastructure failures.
#[derive(Clone, Copy)]
pub(crate) enum Change {
    Done,
    Refused(CommonErrorCode),
}

/// The status an admin may set.
pub(crate) const SETTABLE_STATUSES: [&str; 3] = ["active", "suspended", "disabled"];
pub(crate) const ROLES: [&str; 3] = ["reader", "operator", "admin"];

/// The target as locked at the start of a change.
struct Target {
    status: String,
    role: String,
}

/// The chain Invited, Active, Suspended, Disabled; Disabled is terminal.
const TRANSITIONS: [(&str, &str); 6] = [
    ("invited", "active"),
    ("invited", "disabled"),
    ("active", "suspended"),
    ("active", "disabled"),
    ("suspended", "active"),
    ("suspended", "disabled"),
];

fn allowed(from: &str, to: &str) -> bool {
    TRANSITIONS.contains(&(from, to))
}

async fn lock_target(
    connection: &mut PgConnection,
    id: Uuid,
) -> Result<Option<Target>, sqlx::Error> {
    // why: every active admin is locked too, so two concurrent changes cannot both pass the
    // last-admin check.
    sqlx::query(
        "select id from users where role = 'admin' and status = 'active' order by id for update",
    )
    .fetch_all(&mut *connection)
    .await?;
    let row = sqlx::query("select status, role from users where id = $1 for update")
        .bind(id)
        .fetch_optional(connection)
        .await?;
    row.map(|row| {
        Ok(Target {
            status: row.try_get("status")?,
            role: row.try_get("role")?,
        })
    })
    .transpose()
}

/// True when another active admin remains if `id` stops being one.
async fn another_admin(connection: &mut PgConnection, id: Uuid) -> Result<bool, sqlx::Error> {
    sqlx::query_scalar(
        "select exists (select 1 from users where role = 'admin' and status = 'active' and id <> $1)",
    )
    .bind(id)
    .fetch_one(connection)
    .await
}

pub(crate) async fn set_status(request: Request<'_>, status: &str) -> Result<Change, ChangeError> {
    let mut transaction = request.pool.begin().await?;
    let target = lock_target(&mut transaction, request.target).await?;
    let Some(target) = target else {
        return Ok(Change::Refused(CommonErrorCode::NotFound));
    };
    if request.actor == request.target {
        return Ok(Change::Refused(CommonErrorCode::Forbidden));
    }
    if !allowed(&target.status, status) {
        return Ok(Change::Refused(CommonErrorCode::InvalidTransition));
    }
    let leaves_admin = target.role == "admin" && target.status == "active" && status != "active";
    if leaves_admin && !another_admin(&mut transaction, request.target).await? {
        return Ok(Change::Refused(CommonErrorCode::Forbidden));
    }
    apply_status(&mut transaction, request, status).await?;
    transaction.commit().await?;
    Ok(Change::Done)
}

async fn apply_status(
    connection: &mut PgConnection,
    request: Request<'_>,
    status: &str,
) -> Result<(), ChangeError> {
    let version: i64 = sqlx::query_scalar(
        "update users set status = $2, grant_version = grant_version + 1, revision = revision + 1,
                updated_at = $3 where id = $1 returning grant_version",
    )
    .bind(request.target)
    .bind(status)
    .bind(request.now.to_offset_date_time())
    .fetch_one(&mut *connection)
    .await?;
    if status != "active" {
        revoke_sessions(connection, request).await?;
    }
    if status == "disabled" {
        supersede_links(connection, request.target).await?;
    }
    let event = match status {
        "active" => Some("grant.changed"),
        "suspended" | "disabled" => Some("user.disabled"),
        _ => None,
    };
    if let Some(kind) = event {
        emit(connection, request, (kind, version)).await?;
    }
    audit_change(connection, request, &format!("user_status_{status}")).await?;
    Ok(())
}

pub(crate) async fn set_role(request: Request<'_>, role: &str) -> Result<Change, ChangeError> {
    let mut transaction = request.pool.begin().await?;
    let target = lock_target(&mut transaction, request.target).await?;
    let Some(target) = target else {
        return Ok(Change::Refused(CommonErrorCode::NotFound));
    };
    if request.actor == request.target {
        return Ok(Change::Refused(CommonErrorCode::Forbidden));
    }
    if target.role == role {
        return Ok(Change::Refused(CommonErrorCode::InvalidTransition));
    }
    let demotes = target.role == "admin" && target.status == "active";
    if demotes && !another_admin(&mut transaction, request.target).await? {
        return Ok(Change::Refused(CommonErrorCode::Forbidden));
    }
    let version: i64 = sqlx::query_scalar(
        "update users set role = $2, grant_version = grant_version + 1, revision = revision + 1,
                updated_at = $3 where id = $1 returning grant_version",
    )
    .bind(request.target)
    .bind(role)
    .bind(request.now.to_offset_date_time())
    .fetch_one(&mut *transaction)
    .await?;
    emit(&mut transaction, request, ("grant.changed", version)).await?;
    audit_change(&mut transaction, request, &format!("user_role_{role}")).await?;
    transaction.commit().await?;
    Ok(Change::Done)
}

async fn revoke_sessions(
    connection: &mut PgConnection,
    request: Request<'_>,
) -> Result<(), sqlx::Error> {
    sqlx::query("update sessions set revoked_at = $2 where user_id = $1 and revoked_at is null")
        .bind(request.target)
        .bind(request.now.to_offset_date_time())
        .execute(connection)
        .await
        .map(|_| ())
}

async fn supersede_links(connection: &mut PgConnection, user: Uuid) -> Result<(), sqlx::Error> {
    sqlx::query("update links set state = 'superseded' where user_id = $1 and state = 'issued'")
        .bind(user)
        .execute(connection)
        .await
        .map(|_| ())
}

/// Adds an outbox event about the target: its type and the grant version it carries.
async fn emit(
    connection: &mut PgConnection,
    request: Request<'_>,
    event: (&str, i64),
) -> Result<(), ChangeError> {
    let (kind, version) = event;
    let payload = serde_json::json!({
        "user_id": UserId::from_uuid(request.target).to_string(),
        "grant_version": version,
    });
    emit_with(connection, request, Outgoing { kind, payload }).await
}

/// An event type and its ready payload.
pub(crate) struct Outgoing<'a> {
    pub kind: &'a str,
    pub payload: serde_json::Value,
}

/// Adds an outbox event about the target with a ready payload.
pub(crate) async fn emit_with(
    connection: &mut PgConnection,
    request: Request<'_>,
    event: Outgoing<'_>,
) -> Result<(), ChangeError> {
    let Outgoing { kind, payload } = event;
    let id = uuid_v7(request.now.unix_millis(), &OsRandom)?;
    sqlx::query(
        "insert into events (id, type, v, subject_id, payload, at) values ($1, $2, 1, $3, $4, $5)",
    )
    .bind(id)
    .bind(kind)
    .bind(request.target)
    .bind(payload)
    .bind(request.now.to_offset_date_time())
    .execute(connection)
    .await?;
    Ok(())
}

/// Raises the target's grant version and returns the new value.
pub(crate) async fn bump_grant_version(
    connection: &mut PgConnection,
    request: Request<'_>,
) -> Result<i64, sqlx::Error> {
    sqlx::query_scalar(
        "update users set grant_version = grant_version + 1, updated_at = $2 where id = $1
         returning grant_version",
    )
    .bind(request.target)
    .bind(request.now.to_offset_date_time())
    .fetch_one(connection)
    .await
}

pub(crate) async fn audit_change(
    connection: &mut PgConnection,
    request: Request<'_>,
    action: &str,
) -> Result<(), sqlx::Error> {
    let actor = UserId::from_uuid(request.actor).to_string();
    let subject = UserId::from_uuid(request.target).to_string();
    let entry = AuditEntry {
        at: request.now,
        actor: &actor,
        subject: Some(&subject),
        action,
        address: None,
    };
    audit::record(connection, entry).await
}

/// Resets the one-time read counter of a user and book (idempotent).
pub(crate) async fn reset_read_once(
    request: Request<'_>,
    book: Uuid,
) -> Result<Change, ChangeError> {
    let mut transaction = request.pool.begin().await?;
    let exists: bool = sqlx::query_scalar("select exists (select 1 from users where id = $1)")
        .bind(request.target)
        .fetch_one(&mut *transaction)
        .await?;
    if !exists {
        return Ok(Change::Refused(CommonErrorCode::NotFound));
    }
    sqlx::query("delete from read_once_uses where user_id = $1 and book_id = $2")
        .bind(request.target)
        .bind(book)
        .execute(&mut *transaction)
        .await?;
    audit_change(&mut transaction, request, "read_once_reset").await?;
    transaction.commit().await?;
    Ok(Change::Done)
}

/// Deletes an account on request: its sessions, credentials, grants and mail requests go with
/// it, and a `user.deleted` event tells the other services to erase what they hold (D-76).
pub(crate) async fn delete_user(request: Request<'_>) -> Result<Change, ChangeError> {
    let mut transaction = request.pool.begin().await?;
    let target = lock_target(&mut transaction, request.target).await?;
    let Some(target) = target else {
        return Ok(Change::Refused(CommonErrorCode::NotFound));
    };
    if request.actor == request.target {
        return Ok(Change::Refused(CommonErrorCode::Forbidden));
    }
    let is_active_admin = target.role == "admin" && target.status == "active";
    if is_active_admin && !another_admin(&mut transaction, request.target).await? {
        return Ok(Change::Refused(CommonErrorCode::Forbidden));
    }
    sqlx::query("delete from users where id = $1")
        .bind(request.target)
        .execute(&mut *transaction)
        .await?;
    announce_deleted(&mut transaction, request).await?;
    audit_change(&mut transaction, request, "user_deleted").await?;
    transaction.commit().await?;
    Ok(Change::Done)
}

async fn announce_deleted(
    connection: &mut PgConnection,
    request: Request<'_>,
) -> Result<(), ChangeError> {
    let payload = serde_json::json!({ "user_id": UserId::from_uuid(request.target).to_string() });
    let event = Outgoing {
        kind: "user.deleted",
        payload,
    };
    emit_with(connection, request, event).await
}
