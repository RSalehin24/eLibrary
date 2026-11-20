//! Cover validation at intake (planning/05-services/catalog/files.md): the type comes from the
//! bytes, never from a name or a declared media type, and the size and dimensions stay in range.
//! Only headers are read; nothing is decoded, so a hostile image cannot cost more than its length.

/// Largest accepted cover file.
pub const MAX_COVER_BYTES: usize = 5 * 1024 * 1024;
/// Largest accepted side in pixels; limits are mine, not yet in the limits table.
pub const MAX_COVER_SIDE: u32 = 4000;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CoverKind {
    Jpeg,
    Png,
    Webp,
}

impl CoverKind {
    #[must_use]
    pub fn media_type(self) -> &'static str {
        match self {
            Self::Jpeg => "image/jpeg",
            Self::Png => "image/png",
            Self::Webp => "image/webp",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Cover {
    pub kind: CoverKind,
    pub width: u32,
    pub height: u32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CoverError {
    TooLarge,
    UnknownType,
    Malformed,
    BadDimensions,
}

/// The cover's type and size, or the reason it is refused.
///
/// # Errors
/// The file is too large, is not JPEG, PNG or WebP, has a damaged header, or has a side of 0 or
/// more than [`MAX_COVER_SIDE`].
pub fn validate(bytes: &[u8]) -> Result<Cover, CoverError> {
    if bytes.len() > MAX_COVER_BYTES {
        return Err(CoverError::TooLarge);
    }
    let (kind, size) = if bytes.starts_with(&[0x89, b'P', b'N', b'G', 0x0d, 0x0a, 0x1a, 0x0a]) {
        (CoverKind::Png, png_size(bytes))
    } else if bytes.starts_with(&[0xff, 0xd8, 0xff]) {
        (CoverKind::Jpeg, jpeg_size(bytes))
    } else if bytes.starts_with(b"RIFF") && bytes.get(8..12) == Some(b"WEBP".as_slice()) {
        (CoverKind::Webp, webp_size(bytes))
    } else {
        return Err(CoverError::UnknownType);
    };
    let (width, height) = size.ok_or(CoverError::Malformed)?;
    let in_range = |side: u32| (1..=MAX_COVER_SIDE).contains(&side);
    if in_range(width) && in_range(height) {
        Ok(Cover {
            kind,
            width,
            height,
        })
    } else {
        Err(CoverError::BadDimensions)
    }
}

fn be32(bytes: &[u8], at: usize) -> Option<u32> {
    let raw = bytes.get(at..at.checked_add(4)?)?;
    Some(u32::from_be_bytes(raw.try_into().ok()?))
}

fn be16(bytes: &[u8], at: usize) -> Option<u32> {
    let raw = bytes.get(at..at.checked_add(2)?)?;
    Some(u32::from(u16::from_be_bytes(raw.try_into().ok()?)))
}

fn le_bits(bytes: &[u8], at: usize, count: usize) -> Option<u32> {
    let raw = bytes.get(at..at.checked_add(count)?)?;
    Some(
        raw.iter()
            .rev()
            .fold(0_u32, |acc, byte| (acc << 8) | u32::from(*byte)),
    )
}

/// The first chunk must be IHDR: 8 signature bytes, length, `IHDR`, then width and height.
fn png_size(bytes: &[u8]) -> Option<(u32, u32)> {
    (bytes.get(12..16)? == b"IHDR").then_some(())?;
    Some((be32(bytes, 16)?, be32(bytes, 20)?))
}

/// Walks the marker segments up to the first start-of-frame, which holds the size.
fn jpeg_size(bytes: &[u8]) -> Option<(u32, u32)> {
    let mut at = 2;
    loop {
        match jpeg_step(bytes, at)? {
            JpegStep::Frame(size) => return Some(size),
            JpegStep::Next(next) => at = next,
        }
    }
}

enum JpegStep {
    Frame((u32, u32)),
    Next(usize),
}

fn jpeg_step(bytes: &[u8], at: usize) -> Option<JpegStep> {
    let marker = match (bytes.get(at)?, bytes.get(at.checked_add(1)?)?) {
        (0xff, 0xff) => return Some(JpegStep::Next(at.checked_add(1)?)),
        (0xff, marker) => *marker,
        _ => return None,
    };
    let length = usize::try_from(be16(bytes, at.checked_add(2)?)?).ok()?;
    let is_frame = matches!(marker, 0xc0..=0xcf) && !matches!(marker, 0xc4 | 0xc8 | 0xcc);
    let ends_scan = length < 2 || marker == 0xda;
    match (is_frame, ends_scan) {
        (true, _) => Some(JpegStep::Frame((
            be16(bytes, at.checked_add(7)?)?,
            be16(bytes, at.checked_add(5)?)?,
        ))),
        (false, true) => None,
        (false, false) => Some(JpegStep::Next(at.checked_add(2)?.checked_add(length)?)),
    }
}

fn webp_size(bytes: &[u8]) -> Option<(u32, u32)> {
    match bytes.get(12..16)? {
        b"VP8 " => {
            (bytes.get(23..26)? == [0x9d, 0x01, 0x2a]).then_some(())?;
            Some((
                le_bits(bytes, 26, 2)? & 0x3fff,
                le_bits(bytes, 28, 2)? & 0x3fff,
            ))
        }
        b"VP8L" => {
            (*bytes.get(20)? == 0x2f).then_some(())?;
            let packed = le_bits(bytes, 21, 4)?;
            Some(((packed & 0x3fff) + 1, ((packed >> 14) & 0x3fff) + 1))
        }
        b"VP8X" => Some((le_bits(bytes, 24, 3)? + 1, le_bits(bytes, 27, 3)? + 1)),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::{Cover, CoverError, CoverKind, MAX_COVER_BYTES, MAX_COVER_SIDE, validate};

    fn png(width: u32, height: u32) -> Vec<u8> {
        let mut bytes = vec![0x89, b'P', b'N', b'G', 0x0d, 0x0a, 0x1a, 0x0a, 0, 0, 0, 13];
        bytes.extend_from_slice(b"IHDR");
        bytes.extend_from_slice(&width.to_be_bytes());
        bytes.extend_from_slice(&height.to_be_bytes());
        bytes
    }

    fn jpeg(width: u16, height: u16) -> Vec<u8> {
        let mut bytes = vec![0xff, 0xd8, 0xff, 0xe0, 0, 4, 0, 0, 0xff, 0xc0, 0, 11, 8];
        bytes.extend_from_slice(&height.to_be_bytes());
        bytes.extend_from_slice(&width.to_be_bytes());
        bytes
    }

    fn webp(chunk: [u8; 4], body: &[u8]) -> Vec<u8> {
        let mut bytes = b"RIFF\0\0\0\0WEBP".to_vec();
        bytes.extend_from_slice(&chunk);
        bytes.extend_from_slice(&[0; 4]);
        bytes.extend_from_slice(body);
        bytes
    }

    fn truncated(mut bytes: Vec<u8>, len: usize) -> &'static [u8] {
        bytes.truncate(len);
        Vec::leak(bytes)
    }

    fn found(kind: CoverKind, width: u32, height: u32) -> Cover {
        Cover {
            kind,
            width,
            height,
        }
    }

    #[test]
    fn reads_png_and_jpeg_sizes_from_the_header() {
        assert_eq!(
            validate(&png(600, 900)),
            Ok(found(CoverKind::Png, 600, 900))
        );
        assert_eq!(
            validate(&jpeg(600, 900)),
            Ok(found(CoverKind::Jpeg, 600, 900))
        );
    }

    #[test]
    fn reads_all_three_webp_layouts() {
        let lossy = webp(
            *b"VP8 ",
            &[0, 0, 0, 0x9d, 0x01, 0x2a, 0x58, 0x02, 0x84, 0x03],
        );
        assert_eq!(validate(&lossy), Ok(found(CoverKind::Webp, 600, 900)));
        let width_minus_1 = 599_u32;
        let height_minus_1 = 899_u32;
        let packed = width_minus_1 | (height_minus_1 << 14);
        let mut body = vec![0x2f];
        body.extend_from_slice(&packed.to_le_bytes());
        assert_eq!(
            validate(&webp(*b"VP8L", &body)),
            Ok(found(CoverKind::Webp, 600, 900))
        );
        let mut extended = vec![0; 4];
        extended.extend_from_slice(&[0x57, 0x02, 0]);
        extended.extend_from_slice(&[0x83, 0x03, 0]);
        assert_eq!(
            validate(&webp(*b"VP8X", &extended)),
            Ok(found(CoverKind::Webp, 600, 900))
        );
    }

    #[test]
    fn refuses_other_types_by_their_bytes() {
        let svg = b"<svg xmlns='http://www.w3.org/2000/svg'/>";
        assert_eq!(validate(svg), Err(CoverError::UnknownType));
        assert_eq!(validate(b"GIF89a"), Err(CoverError::UnknownType));
        assert_eq!(validate(b""), Err(CoverError::UnknownType));
    }

    #[test]
    fn refuses_truncated_headers() {
        assert_eq!(
            validate(truncated(png(600, 900), 20)),
            Err(CoverError::Malformed)
        );
        assert_eq!(
            validate(truncated(jpeg(600, 900), 10)),
            Err(CoverError::Malformed)
        );
        assert_eq!(
            validate(b"RIFF\0\0\0\0WEBPVP8 "),
            Err(CoverError::Malformed)
        );
    }

    #[test]
    fn refuses_zero_and_oversized_sides() {
        assert_eq!(validate(&png(0, 900)), Err(CoverError::BadDimensions));
        assert_eq!(
            validate(&png(MAX_COVER_SIDE + 1, 900)),
            Err(CoverError::BadDimensions)
        );
        assert!(validate(&png(MAX_COVER_SIDE, MAX_COVER_SIDE)).is_ok());
    }

    #[test]
    fn refuses_a_file_over_the_size_cap_before_reading_it() {
        let mut big = png(600, 900);
        big.resize(MAX_COVER_BYTES + 1, 0);
        assert_eq!(validate(&big), Err(CoverError::TooLarge));
    }
}
