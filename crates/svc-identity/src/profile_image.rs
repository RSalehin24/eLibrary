//! The profile image (REQ-IDN-034, D-44, D-88): only PNG, JPEG and WebP, recognised by their
//! bytes and checked for a complete file, at most 2 MiB; SVG and everything else is refused.
//! It is stored here and served only to its owner and to administrators.

use sha2::{Digest, Sha256};
use sqlx::{PgPool, Row};
use uuid::Uuid;

use platform_time::Instant;

/// Largest accepted image, in bytes.
pub(crate) const MAX_BYTES: usize = 2 * 1024 * 1024;

const PNG_START: [u8; 8] = [0x89, b'P', b'N', b'G', 0x0d, 0x0a, 0x1a, 0x0a];
const PNG_END: [u8; 8] = [b'I', b'E', b'N', b'D', 0xae, 0x42, 0x60, 0x82];
const JPEG_START: [u8; 3] = [0xff, 0xd8, 0xff];
const JPEG_END: [u8; 2] = [0xff, 0xd9];

/// The image types we store.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum ImageType {
    Png,
    Jpeg,
    Webp,
}

impl ImageType {
    pub(crate) fn content_type(self) -> &'static str {
        match self {
            Self::Png => "image/png",
            Self::Jpeg => "image/jpeg",
            Self::Webp => "image/webp",
        }
    }
}

/// The type of a complete, plausible image, or `None`.
pub(crate) fn sniff(bytes: &[u8]) -> Option<ImageType> {
    if bytes.is_empty() || bytes.len() > MAX_BYTES {
        return None;
    }
    if bytes.starts_with(&PNG_START) && bytes.ends_with(&PNG_END) {
        return Some(ImageType::Png);
    }
    if bytes.starts_with(&JPEG_START) && bytes.ends_with(&JPEG_END) {
        return Some(ImageType::Jpeg);
    }
    is_webp(bytes).then_some(ImageType::Webp)
}

/// `RIFF <size> WEBP` where the size matches the file.
fn is_webp(bytes: &[u8]) -> bool {
    let Some(header) = bytes.get(..12) else {
        return false;
    };
    let declared = header
        .get(4..8)
        .and_then(|size| <[u8; 4]>::try_from(size).ok())
        .map(u32::from_le_bytes);
    let sized = declared.is_some_and(|size| u64::from(size) + 8 == bytes.len() as u64);
    header.starts_with(b"RIFF") && header.get(8..) == Some(b"WEBP") && sized
}

/// A stored image.
pub(crate) struct Stored {
    pub content_type: String,
    pub bytes: Vec<u8>,
}

/// Replaces the user's image.
pub(crate) async fn save(
    pool: &PgPool,
    owner: (Uuid, Instant),
    image: (ImageType, &[u8]),
) -> Result<(), sqlx::Error> {
    let (user, now) = owner;
    let (kind, bytes) = image;
    let size = i32::try_from(bytes.len()).unwrap_or(i32::MAX);
    sqlx::query(
        "insert into profile_images (user_id, content_type, bytes, size, sha256, updated_at)
         values ($1, $2, $3, $4, $5, $6)
         on conflict (user_id) do update set content_type = $2, bytes = $3, size = $4,
             sha256 = $5, updated_at = $6",
    )
    .bind(user)
    .bind(kind.content_type())
    .bind(bytes)
    .bind(size)
    .bind(Sha256::digest(bytes).to_vec())
    .bind(now.to_offset_date_time())
    .execute(pool)
    .await
    .map(|_| ())
}

pub(crate) async fn remove(pool: &PgPool, user: Uuid) -> Result<(), sqlx::Error> {
    sqlx::query("delete from profile_images where user_id = $1")
        .bind(user)
        .execute(pool)
        .await
        .map(|_| ())
}

pub(crate) async fn load(pool: &PgPool, user: Uuid) -> Result<Option<Stored>, sqlx::Error> {
    let row = sqlx::query("select content_type, bytes from profile_images where user_id = $1")
        .bind(user)
        .fetch_optional(pool)
        .await?;
    row.map(|row| {
        Ok(Stored {
            content_type: row.try_get("content_type")?,
            bytes: row.try_get("bytes")?,
        })
    })
    .transpose()
}

#[cfg(test)]
mod tests {
    use super::{ImageType, MAX_BYTES, PNG_END, PNG_START, sniff};

    fn png() -> Vec<u8> {
        [PNG_START.as_slice(), b"data", PNG_END.as_slice()].concat()
    }

    #[test]
    fn recognises_complete_png_jpeg_and_webp() {
        assert_eq!(sniff(&png()), Some(ImageType::Png));
        assert_eq!(
            sniff(&[0xff, 0xd8, 0xff, 0xe0, 1, 2, 0xff, 0xd9]),
            Some(ImageType::Jpeg)
        );
        let mut webp = b"RIFF".to_vec();
        webp.extend_from_slice(&8_u32.to_le_bytes());
        webp.extend_from_slice(b"WEBPabcd");
        assert_eq!(sniff(&webp), Some(ImageType::Webp));
    }

    #[test]
    fn refuses_svg_truncated_wrong_sized_and_oversized_files() {
        assert_eq!(sniff(b"<svg xmlns='http://www.w3.org/2000/svg'/>"), None);
        let mut truncated = png();
        truncated.truncate(truncated.len() - 2);
        assert_eq!(sniff(&truncated), None);
        assert_eq!(sniff(&[]), None);
        let mut webp = b"RIFF".to_vec();
        webp.extend_from_slice(&99_u32.to_le_bytes());
        webp.extend_from_slice(b"WEBPabcd");
        assert_eq!(sniff(&webp), None);
        let big = [
            PNG_START.as_slice(),
            &vec![0; MAX_BYTES],
            PNG_END.as_slice(),
        ]
        .concat();
        assert_eq!(sniff(&big), None);
    }
}
