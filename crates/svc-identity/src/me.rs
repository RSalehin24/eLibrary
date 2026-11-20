//! The signed-in user's own account: the profile and the fields they may change.

use domain_text::DisplayText;
use platform_time::Instant;
use serde::{Deserialize, Serialize};
use sqlx::{PgPool, Row};
use uuid::Uuid;

/// Longest display name, in characters.
// why: no value is in the limits table yet; kept here until it is (TBD-P0).
const DISPLAY_NAME_MAX: usize = 100;

#[derive(Serialize)]
pub(crate) struct Me {
    id: String,
    email: String,
    display_name: String,
    language: String,
    role: String,
    status: String,
    has_image: bool,
    totp_enabled: bool,
}

pub(crate) async fn find(pool: &PgPool, id: Uuid) -> Result<Option<Me>, sqlx::Error> {
    let row = sqlx::query(
        "select u.id, u.email, u.display_name, u.language, u.role, u.status,
                exists (select 1 from profile_images i where i.user_id = u.id) as has_image,
                exists (select 1 from totp t where t.user_id = u.id and t.state = 'enabled') as totp_enabled
         from users u where u.id = $1 and u.status = 'active'",
    )
    .bind(id)
    .fetch_optional(pool)
    .await?;
    row.map(|row| {
        Ok(Me {
            id: contracts_ids::UserId::from_uuid(row.try_get("id")?).to_string(),
            email: row.try_get("email")?,
            display_name: row.try_get("display_name")?,
            language: row.try_get("language")?,
            role: row.try_get("role")?,
            status: row.try_get("status")?,
            has_image: row.try_get("has_image")?,
            totp_enabled: row.try_get("totp_enabled")?,
        })
    })
    .transpose()
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Change {
    display_name: Option<String>,
    language: Option<String>,
}

/// A change that passed validation, ready to store.
pub(crate) struct Edit {
    id: Uuid,
    at: Instant,
    display_name: Option<DisplayText>,
    language: Option<String>,
}

pub(crate) fn valid_name(raw: &str) -> Option<DisplayText> {
    let name = DisplayText::new(raw.trim());
    let length = name.as_str().chars().count();
    let clean = !name.as_str().chars().any(char::is_control);
    (clean && (1..=DISPLAY_NAME_MAX).contains(&length)).then_some(name)
}

/// The first field that is wrong, as the error's field name.
pub(crate) fn validate(change: Change, id: Uuid, at: Instant) -> Result<Edit, &'static str> {
    if change.display_name.is_none() && change.language.is_none() {
        return Err("body");
    }
    let display_name = change.display_name.as_deref().map(valid_name);
    if matches!(display_name, Some(None)) {
        return Err("display_name");
    }
    if !change
        .language
        .as_deref()
        .is_none_or(|code| matches!(code, "bn" | "en"))
    {
        return Err("language");
    }
    Ok(Edit {
        id,
        at,
        display_name: display_name.flatten(),
        language: change.language,
    })
}

/// Applies the change; false when the account is no longer active.
pub(crate) async fn update(pool: &PgPool, edit: Edit) -> Result<bool, sqlx::Error> {
    let result = sqlx::query(
        "update users set display_name = coalesce($2, display_name), language = coalesce($3, language),
                revision = revision + 1, updated_at = $4
         where id = $1 and status = 'active'",
    )
    .bind(edit.id)
    .bind(edit.display_name.as_ref().map(DisplayText::as_str))
    .bind(edit.language)
    .bind(edit.at.to_offset_date_time())
    .execute(pool)
    .await?;
    Ok(result.rows_affected() == 1)
}

/// How an administrator's profile edit ended.
pub(crate) enum Edited {
    Done,
    NotFound,
    Stale,
}

/// Applies the edit to the account (any status) only at the revision the caller saw.
pub(crate) async fn update_at_revision(
    pool: &PgPool,
    edit: Edit,
    revision: i64,
) -> Result<Edited, sqlx::Error> {
    let result = sqlx::query(
        "update users set display_name = coalesce($2, display_name), language = coalesce($3, language),
                revision = revision + 1, updated_at = $4
         where id = $1 and revision = $5",
    )
    .bind(edit.id)
    .bind(edit.display_name.as_ref().map(DisplayText::as_str))
    .bind(&edit.language)
    .bind(edit.at.to_offset_date_time())
    .bind(revision)
    .execute(pool)
    .await?;
    if result.rows_affected() == 1 {
        return Ok(Edited::Done);
    }
    let exists: bool = sqlx::query_scalar("select exists (select 1 from users where id = $1)")
        .bind(edit.id)
        .fetch_one(pool)
        .await?;
    Ok(if exists {
        Edited::Stale
    } else {
        Edited::NotFound
    })
}
