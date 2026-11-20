//! Inviting people: a new account in the `invited` state plus a setup link, and new links for
//! accounts still waiting (REQ-IDN-001, REQ-IDN-031).

use contracts_http::CommonErrorCode;
use domain_credentials::Email;
use domain_text::DisplayText;
use platform_random::{OsRandom, uuid_v7};
use sqlx::{PgConnection, PgPool};
use uuid::Uuid;

use crate::admin_change::{Request, audit_change};
use crate::links::{Issue, LinkError, Purpose, issue};
use crate::vault::VaultKey;

/// The checked fields of an invitation.
pub(crate) struct Person<'a> {
    pub email: Email,
    pub display_name: DisplayText,
    pub role: &'a str,
    pub language: &'a str,
}

/// How an invitation or resend ended, apart from infrastructure failures.
#[derive(Clone, Copy)]
pub(crate) enum Invited {
    Done(Uuid),
    EmailTaken,
    Refused(CommonErrorCode),
}

/// The pool, vault key and the acting administrator with the time.
#[derive(Clone, Copy)]
pub(crate) struct Inviter<'a> {
    pub pool: &'a PgPool,
    pub key: &'a VaultKey,
    pub request: Request<'a>,
}

fn is_unique_violation(error: &sqlx::Error) -> bool {
    error
        .as_database_error()
        .is_some_and(|db| db.code().as_deref() == Some("23505"))
}

/// Inserts the invited account; false when the address already has an account.
async fn insert_user(
    connection: &mut PgConnection,
    request: Request<'_>,
    person: &Person<'_>,
) -> Result<bool, sqlx::Error> {
    let inserted = sqlx::query(
        "insert into users (id, email, display_name, language, status, role, created_at, updated_at)
         values ($1, $2, $3, $4, 'invited', $5, $6, $6)",
    )
    .bind(request.target)
    .bind(person.email.as_str())
    .bind(person.display_name.as_str())
    .bind(person.language)
    .bind(person.role)
    .bind(request.now.to_offset_date_time())
    .execute(connection)
    .await;
    match inserted {
        Err(error) if is_unique_violation(&error) => Ok(false),
        Err(error) => Err(error),
        Ok(_) => Ok(true),
    }
}

/// Creates the invited account and its first setup link in one transaction.
pub(crate) async fn invite(inviter: Inviter<'_>, person: Person<'_>) -> Result<Invited, LinkError> {
    let id = uuid_v7(inviter.request.now.unix_millis(), &OsRandom)?;
    let request = Request {
        target: id,
        ..inviter.request
    };
    let mut transaction = inviter.pool.begin().await?;
    if !insert_user(&mut transaction, request, &person).await? {
        return Ok(Invited::EmailTaken);
    }
    let link = Issue {
        request,
        purpose: Purpose::Invite,
        language: person.language,
    };
    issue(&mut transaction, inviter.key, link).await?;
    audit_change(&mut transaction, request, "user_invited").await?;
    transaction.commit().await?;
    Ok(Invited::Done(id))
}

/// Issues a new setup link for an account that is still `invited`.
pub(crate) async fn resend(inviter: Inviter<'_>) -> Result<Invited, LinkError> {
    let request = inviter.request;
    let mut transaction = inviter.pool.begin().await?;
    let row: Option<(String, String)> =
        sqlx::query_as("select status, language from users where id = $1 for update")
            .bind(request.target)
            .fetch_optional(&mut *transaction)
            .await?;
    let Some((status, language)) = row else {
        return Ok(Invited::Refused(CommonErrorCode::NotFound));
    };
    if status != "invited" {
        return Ok(Invited::Refused(CommonErrorCode::InvalidTransition));
    }
    let link = Issue {
        request,
        purpose: Purpose::Invite,
        language: &language,
    };
    issue(&mut transaction, inviter.key, link).await?;
    audit_change(&mut transaction, request, "invite_resent").await?;
    transaction.commit().await?;
    Ok(Invited::Done(request.target))
}
