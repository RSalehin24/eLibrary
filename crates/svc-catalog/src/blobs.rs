//! The blob store (INV-CAT-020, 021): content addressed and write-once under one root. A path
//! derives from the SHA-256 alone, so no caller input can name a place outside the root.

use std::io;
use std::path::{Path, PathBuf};

use platform_config::{ConfigError, ConfigSource};
use sha2::{Digest as _, Sha256};
use uuid::Uuid;

const ROOT_KEY: &str = "ELIBRARY_BLOB_ROOT";
const TEMP_DIR: &str = "tmp";

/// A SHA-256 as 64 lowercase hex digits; the only way to name a blob.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BlobId(String);

impl BlobId {
    #[must_use]
    pub fn parse(text: &str) -> Option<Self> {
        let well_formed =
            text.len() == 64 && text.bytes().all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f'));
        well_formed.then(|| Self(text.to_owned()))
    }

    fn of(bytes: &[u8]) -> Self {
        Self(hex(&Sha256::digest(bytes)))
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[derive(Debug, Clone)]
pub struct BlobStore {
    root: PathBuf,
}

impl BlobStore {
    /// The store at `root`, which must be an existing directory.
    ///
    /// # Errors
    /// `root` is missing or not a directory.
    pub fn open(root: impl Into<PathBuf>) -> io::Result<Self> {
        let root = root.into();
        let is_dir = std::fs::metadata(&root)?.is_dir();
        is_dir.then_some(Self { root }).ok_or_else(not_a_directory)
    }

    /// The store named by `ELIBRARY_BLOB_ROOT`.
    ///
    /// # Errors
    /// The setting is missing, or the directory is not usable.
    pub fn from_config(source: &impl ConfigSource) -> Result<Self, ConfigError> {
        let path = source
            .get(ROOT_KEY)
            .filter(|text| !text.is_empty())
            .ok_or_else(|| ConfigError::Missing {
                key: ROOT_KEY.to_owned(),
            })?;
        Self::open(path).map_err(|_| ConfigError::InvalidValue {
            key: ROOT_KEY.to_owned(),
        })
    }

    /// `ab/cd/<sha256>` under the root.
    fn path_of(&self, id: &BlobId) -> PathBuf {
        let hex = id.as_str();
        let (first, rest) = hex.split_at(2);
        self.root.join(first).join(&rest[..2]).join(hex)
    }

    /// Stores `bytes` and returns their id. Writing the same bytes again changes nothing; a blob
    /// is never replaced. The file is complete and synced before it appears under its name.
    ///
    /// # Errors
    /// The disk refused the write.
    pub async fn put(&self, bytes: &[u8]) -> io::Result<BlobId> {
        let id = BlobId::of(bytes);
        let target = self.path_of(&id);
        store_unless_present(&self.root, &target, bytes).await?;
        Ok(id)
    }

    /// The blob's bytes, or `None` when it is absent. A blob whose bytes no longer hash to its id
    /// is an error, never a response.
    ///
    /// # Errors
    /// The read failed, or the stored bytes do not match the id.
    pub async fn read(&self, id: &BlobId) -> io::Result<Option<Vec<u8>>> {
        let read = tokio::fs::read(self.path_of(id)).await;
        checked(id, read)
    }
}

fn not_a_directory() -> io::Error {
    io::Error::new(io::ErrorKind::NotADirectory, "blob root is not a directory")
}

fn checked(id: &BlobId, read: io::Result<Vec<u8>>) -> io::Result<Option<Vec<u8>>> {
    match read {
        Ok(bytes) if BlobId::of(&bytes) == *id => Ok(Some(bytes)),
        Ok(_) => Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "blob does not match its hash",
        )),
        Err(error) if error.kind() == io::ErrorKind::NotFound => Ok(None),
        Err(error) => Err(error),
    }
}

/// Writes through a temp file, then renames into place; rename within one volume is atomic and a
/// racing writer of the same bytes wins harmlessly.
async fn store_unless_present(root: &Path, target: &Path, bytes: &[u8]) -> io::Result<()> {
    if tokio::fs::try_exists(target).await? {
        return Ok(());
    }
    store_file(&root.join(TEMP_DIR), target, bytes).await
}

async fn store_file(temp_dir: &Path, target: &Path, bytes: &[u8]) -> io::Result<()> {
    tokio::fs::create_dir_all(temp_dir).await?;
    let temp = temp_dir.join(Uuid::now_v7().to_string());
    write_synced(&temp, bytes).await?;
    let parent = target
        .parent()
        .ok_or_else(|| io::Error::other("blob path has no parent"))?;
    tokio::fs::create_dir_all(parent).await?;
    let moved = tokio::fs::rename(&temp, target).await;
    if moved.is_err() {
        drop(tokio::fs::remove_file(&temp).await);
    }
    moved
}

async fn write_synced(path: &Path, bytes: &[u8]) -> io::Result<()> {
    use tokio::io::AsyncWriteExt;
    let mut file = tokio::fs::File::create_new(path).await?;
    file.write_all(bytes).await?;
    file.sync_all().await
}

fn hex(bytes: &[u8]) -> String {
    bytes
        .iter()
        .flat_map(|byte| [byte >> 4, byte & 0x0f])
        .filter_map(|nibble| char::from_digit(u32::from(nibble), 16))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::BlobId;

    #[test]
    fn ids_accept_only_lowercase_sha256_hex() {
        assert!(BlobId::parse(&"a".repeat(64)).is_some());
        let bad = [
            "A".repeat(64),
            "a".repeat(63),
            "../etc/passwd".to_owned(),
            String::new(),
        ];
        assert!(bad.iter().all(|text| BlobId::parse(text).is_none()));
    }

    #[test]
    fn the_id_of_known_bytes_is_their_sha256() {
        let empty = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
        assert_eq!(BlobId::of(b"").as_str(), empty);
    }
}
