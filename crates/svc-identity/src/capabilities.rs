//! The one resolved capability set the web app derives navigation and guards from.

use contracts_http::Scope;
use domain_access::{Role, role_scopes};
use platform_time::Instant;
use serde::Serialize;
use sqlx::{PgPool, Row};
use uuid::Uuid;

#[derive(Serialize)]
pub(crate) struct Capabilities {
    role: String,
    scopes: Vec<&'static str>,
    totp: &'static str,
}

impl Capabilities {
    /// The wire names of the resolved scopes, sorted.
    pub(crate) fn scope_names(&self) -> &[&'static str] {
        &self.scopes
    }

    /// True when the wire name of the scope is in the set.
    pub(crate) fn allows(&self, scope: Scope) -> bool {
        self.scopes.contains(&scope.as_str())
    }
}

fn role_of(name: &str) -> Option<Role> {
    match name {
        "reader" => Some(Role::Reader),
        "operator" => Some(Role::Operator),
        "admin" => Some(Role::Admin),
        _ => None,
    }
}

fn scope_of(name: &str) -> Option<Scope> {
    Scope::ALL.into_iter().find(|scope| scope.as_str() == name)
}

pub(crate) fn totp_state(state: &str, required: bool) -> &'static str {
    match (state, required) {
        ("enabled", _) => "on",
        ("pending", _) => "pending",
        (_, true) => "required",
        _ => "off",
    }
}

/// Role scopes plus the account's live global grants, sorted and without duplicates.
fn scope_names(role: &str, granted: &[String]) -> Vec<&'static str> {
    let mut scopes: Vec<Scope> = role_of(role).map_or(&[][..], role_scopes).to_vec();
    scopes.extend(granted.iter().filter_map(|name| scope_of(name)));
    let mut names: Vec<&'static str> = scopes.into_iter().map(Scope::as_str).collect();
    names.sort_unstable();
    names.dedup();
    names
}

/// The capability set; per-book grants are decided per book and are not part of it.
pub(crate) async fn resolve(
    pool: &PgPool,
    id: Uuid,
    now: Instant,
) -> Result<Option<Capabilities>, sqlx::Error> {
    let Some(user) = sqlx::query(
        "select role, totp_required,
                coalesce((select t.state from totp t where t.user_id = u.id), 'none') as totp_state
         from users u where u.id = $1 and u.status = 'active'",
    )
    .bind(id)
    .fetch_optional(pool)
    .await?
    else {
        return Ok(None);
    };
    let granted: Vec<String> = sqlx::query_scalar(
        "select scope from grants
         where user_id = $1 and active and book_id is null and (expires_at is null or expires_at > $2)",
    )
    .bind(id)
    .bind(now.to_offset_date_time())
    .fetch_all(pool)
    .await?;
    let role: String = user.try_get("role")?;
    let state: String = user.try_get("totp_state")?;
    Ok(Some(Capabilities {
        scopes: scope_names(&role, &granted),
        totp: totp_state(&state, user.try_get("totp_required")?),
        role,
    }))
}
