use axum::body::Body;
use axum::http::{Request, StatusCode};
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};

use platform_http::{ContractVersion, DependencyProbe, InternalChecks, Readiness, internal_router};
use tower::ServiceExt;

async fn status(
    readiness: &Readiness,
    path: &str,
) -> Result<StatusCode, Box<dyn std::error::Error>> {
    let router = internal_router(InternalChecks::without_dependencies(
        readiness.clone(),
        ContractVersion(3),
    ));
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
    let router = internal_router(InternalChecks::without_dependencies(
        Readiness::default(),
        ContractVersion(3),
    ));
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

fn flag_probe(flag: Arc<AtomicBool>) -> DependencyProbe {
    Arc::new(move || Box::pin(std::future::ready(flag.load(Ordering::SeqCst))))
}

async fn ready_status(checks: InternalChecks) -> Result<StatusCode, Box<dyn std::error::Error>> {
    let request = Request::builder()
        .uri("/internal/ready")
        .body(Body::empty())?;
    Ok(internal_router(checks).oneshot(request).await?.status())
}

#[tokio::test]
async fn ready_follows_the_dependency_probe() -> Result<(), Box<dyn std::error::Error>> {
    let healthy = Arc::new(AtomicBool::new(true));
    let readiness = Readiness::default();
    readiness.mark_ready();
    let checks = InternalChecks {
        readiness,
        contract: ContractVersion(3),
        dependencies: flag_probe(Arc::clone(&healthy)),
    };
    assert_eq!(ready_status(checks.clone()).await?, StatusCode::OK);
    healthy.store(false, Ordering::SeqCst);
    assert_eq!(ready_status(checks).await?, StatusCode::SERVICE_UNAVAILABLE);
    Ok(())
}
