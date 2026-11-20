//! The blob store on a real directory (INV-CAT-020, 021).

use svc_catalog::BlobStore;

fn store() -> std::io::Result<(BlobStore, std::path::PathBuf)> {
    let dir = std::env::temp_dir().join(format!("catalog-blobs-{}", uuid::Uuid::now_v7()));
    std::fs::create_dir_all(&dir)?;
    Ok((BlobStore::open(&dir)?, dir))
}

#[tokio::test]
async fn stores_once_reads_back_and_misses_cleanly() -> std::io::Result<()> {
    let (store, dir) = store()?;
    let first = store.put(b"cover bytes").await?;
    assert_eq!(first, store.put(b"cover bytes").await?);
    assert_eq!(
        store.read(&first).await?.as_deref(),
        Some(&b"cover bytes"[..])
    );
    let absent = store.put(b"other").await?;
    std::fs::remove_dir_all(dir.join("tmp"))?;
    assert!(store.read(&absent).await?.is_some());
    std::fs::remove_dir_all(dir)
}

#[tokio::test]
async fn a_changed_blob_is_an_error_and_a_missing_one_is_none() -> std::io::Result<()> {
    let (store, dir) = store()?;
    let id = store.put(b"original").await?;
    let path = dir
        .join(&id.as_str()[..2])
        .join(&id.as_str()[2..4])
        .join(id.as_str());
    std::fs::write(&path, b"tampered")?;
    assert!(store.read(&id).await.is_err());
    std::fs::remove_file(&path)?;
    assert!(store.read(&id).await?.is_none());
    std::fs::remove_dir_all(dir)
}

#[test]
fn open_refuses_a_missing_root() {
    assert!(BlobStore::open("/nonexistent/catalog/blobs").is_err());
}
