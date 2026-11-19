use platform_time::Instant;
use sqlx::PgConnection;

/// One row of the insert-only audit log (D-40). Secrets never go in `detail`.
pub(crate) struct AuditEntry<'a> {
    pub at: Instant,
    pub actor: &'a str,
    pub subject: Option<&'a str>,
    pub action: &'a str,
    pub address: Option<&'a str>,
}

pub(crate) async fn record(
    connection: &mut PgConnection,
    entry: AuditEntry<'_>,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        "insert into audit_log (at, actor, subject, action, address) values ($1, $2, $3, $4, $5)",
    )
    .bind(entry.at.to_offset_date_time())
    .bind(entry.actor)
    .bind(entry.subject)
    .bind(entry.action)
    .bind(entry.address)
    .execute(connection)
    .await
    .map(|_| ())
}
