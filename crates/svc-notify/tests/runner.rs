//! One full round: pull an event from a stub identity, fetch the mail by reference, send it
//! through the in-memory sink and log it (gate Q4).

use axum::Router;
use axum::http::Uri;
use axum::response::IntoResponse;
use axum::routing::get;
use platform_internal_http::Caller;
use platform_service_token::{KeyId, ServiceName, SigningKey, TokenIssuer};
use platform_testkit::TestDatabase;
use sqlx::PgPool;
use svc_notify::MIGRATIONS;
use svc_notify::runner::{Loops, Round, round};
use svc_notify::transport::SinkTransport;

type Failure = Box<dyn std::error::Error>;

const USER: &str = "00000000-0000-7000-8000-00000000000a";

async fn events() -> impl IntoResponse {
    let payload = serde_json::json!({
        "request_id": "req-1", "kind": "invite", "user_id": USER, "language": "en"
    });
    axum::Json(serde_json::json!({
        "events": [{"cursor": 1, "id": "00000000-0000-7000-8000-0000000000e1", "type": "email.requested",
                    "v": 1, "subject_id": USER, "request_id": null, "payload": payload, "at": 1}],
        "next": 1
    }))
}

async fn mail(uri: Uri) -> impl IntoResponse {
    let found = uri.path().ends_with("/req-1");
    let body = serde_json::json!({"kind": "invite", "to": "new@example.org", "language": "en",
                                  "link": "https://library.test/accept-invite?token=abc"});
    if found {
        (axum::http::StatusCode::OK, axum::Json(body)).into_response()
    } else {
        axum::http::StatusCode::NOT_FOUND.into_response()
    }
}

async fn stub_identity() -> Result<String, Failure> {
    let app = Router::new()
        .route("/internal/events", get(events))
        .route("/internal/email-requests/{id}", get(mail));
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await?;
    let base = format!("http://{}", listener.local_addr()?);
    tokio::spawn(async move { axum::serve(listener, app).await });
    Ok(base)
}

fn loops(pool: PgPool, base: String) -> Result<Loops<SinkTransport>, Failure> {
    let issuer = TokenIssuer::new(
        ServiceName::parse("notify")?,
        KeyId(1),
        SigningKey::new(vec![9; 32])?,
    );
    Ok(Loops {
        pool,
        caller: Caller::new(issuer),
        identity_base: base,
        transport: SinkTransport::default(),
    })
}

#[tokio::test]
#[ignore = "needs the throwaway Postgres (gate Q4)"]
async fn a_round_pulls_fetches_sends_and_logs_without_storing_the_address() -> Result<(), Failure> {
    let pool = TestDatabase::create(&MIGRATIONS).await?.pool;
    let loops = loops(pool.clone(), stub_identity().await?)?;
    assert_eq!(
        round(&loops).await,
        Round {
            pulled: 1,
            handled: 1
        }
    );
    let mails = loops.transport.sent();
    assert_eq!(mails.len(), 1);
    assert_eq!(
        mails.first().map(|mail| mail.to.as_str()),
        Some("new@example.org")
    );
    assert_stored_safely(&pool).await?;
    Ok(())
}

/// The row is `sent` and the delivery log holds only a masked address.
async fn assert_stored_safely(pool: &PgPool) -> Result<(), Failure> {
    let state: String = sqlx::query_scalar("select state from outbox")
        .fetch_one(pool)
        .await?;
    assert_eq!(state, "sent");
    let masked: Option<String> = sqlx::query_scalar("select masked_address from delivery_log")
        .fetch_one(pool)
        .await?;
    assert!(masked.is_some_and(|text| !text.contains("new@example.org")));
    Ok(())
}
