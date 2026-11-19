use sqlx::{PgPool, Row};
use uuid::Uuid;

/// What sign-in needs to know about an account.
pub(crate) struct SignInRecord {
    pub id: Uuid,
    pub status: String,
    pub totp_required: bool,
    pub password_hash: Option<String>,
}

pub(crate) async fn find_for_sign_in(
    pool: &PgPool,
    email: &str,
) -> Result<Option<SignInRecord>, sqlx::Error> {
    let row = sqlx::query(
        "select u.id, u.status, u.totp_required, c.password_hash
         from users u left join credentials c on c.user_id = u.id
         where lower(u.email) = lower($1)",
    )
    .bind(email)
    .fetch_optional(pool)
    .await?;
    row.map(|row| {
        Ok(SignInRecord {
            id: row.try_get("id")?,
            status: row.try_get("status")?,
            totp_required: row.try_get("totp_required")?,
            password_hash: row.try_get("password_hash")?,
        })
    })
    .transpose()
}
