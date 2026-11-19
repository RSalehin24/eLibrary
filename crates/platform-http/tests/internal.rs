use axum::body::Body;
use axum::http::{Request, StatusCode};
use platform_http::{ContractVersion, Readiness, internal_router};
use tower::ServiceExt;

async fn status(
    readiness: &Readiness,
    path: &str,
) -> Result<StatusCode, Box<dyn std::error::Error>> {
    let router = internal_router(readiness.clone(), ContractVersion(3));
    let request = Request::builder().uri(path).body(Body::empty())?;
    Ok(router.oneshot(request).await?.status())
}

#[tokio::test]
async fn health_is_ok_even_before_ready() -> Result<(), Box<dyn std::error::Error>> {
    assert_eq!(
        status(&Readiness::default(), "/internal/health").await?,
        StatusCode::OK
    );
    Ok(())
}

#[tokio::test]
async fn ready_is_unavailable_until_marked() -> Result<(), Box<dyn std::error::Error>> {
    let readiness = Readiness::default();
    assert_eq!(
        status(&readiness, "/internal/ready").await?,
        StatusCode::SERVICE_UNAVAILABLE
    );
    readiness.mark_ready();
    assert_eq!(status(&readiness, "/internal/ready").await?, StatusCode::OK);
    Ok(())
}

#[tokio::test]
async fn contract_endpoint_reports_the_version() -> Result<(), Box<dyn std::error::Error>> {
    let router = internal_router(Readiness::default(), ContractVersion(3));
    let request = Request::builder()
        .uri("/internal/contract")
        .body(Body::empty())?;
    let body = axum::body::to_bytes(router.oneshot(request).await?.into_body(), 64).await?;
    assert_eq!(body.as_ref(), b"3");
    Ok(())
}

#[tokio::test]
async fn unknown_internal_path_is_not_found() -> Result<(), Box<dyn std::error::Error>> {
    assert_eq!(
        status(&Readiness::default(), "/internal/other").await?,
        StatusCode::NOT_FOUND
    );
    Ok(())
}
