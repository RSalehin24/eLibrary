use std::path::Path;

use crate::{ConfigError, ConfigSource, Secret};

const KEY: &str = "ELIBRARY_SERVICE_CALLERS";
const OWN_KEY_FILE: &str = "ELIBRARY_SERVICE_TOKEN_KEY_FILE";
const OWN_KEY_ID: &str = "ELIBRARY_SERVICE_SIGNING_ID";

/// A calling service's service-token key, as named in the settings (D-101).
#[derive(Debug, Clone)]
pub struct PeerKey {
    pub service: String,
    pub key_id: u32,
    /// The secret file's text (hex digits); never printed.
    pub secret: Secret<String>,
}

/// The keys of the services allowed to call this one: `service:kid:/path` entries separated by
/// commas. No setting means no peers (nobody can call).
///
/// # Errors
/// A malformed entry or an unreadable key file.
pub fn read_peer_keys(source: &impl ConfigSource) -> Result<Vec<PeerKey>, ConfigError> {
    let invalid = || ConfigError::InvalidValue {
        key: KEY.to_owned(),
    };
    let Some(list) = source.get(KEY) else {
        return Ok(Vec::new());
    };
    list.split(',')
        .map(str::trim)
        .filter(|entry| !entry.is_empty())
        .map(|entry| parse_entry(entry).ok_or_else(invalid))
        .collect::<Result<Vec<_>, _>>()?
        .into_iter()
        .map(|(service, key_id, path)| load(&service, key_id, Path::new(&path)))
        .collect()
}

/// This service's own signing key and its key id (default 1), when it calls other services.
///
/// # Errors
/// An unreadable key file or a key id that is not a number.
pub fn read_own_signing_key(
    source: &impl ConfigSource,
) -> Result<Option<(u32, Secret<String>)>, ConfigError> {
    if source.get(OWN_KEY_FILE).is_none() {
        return Ok(None);
    }
    let key_id = source.get(OWN_KEY_ID).map_or(Ok(1), |text| {
        text.parse().map_err(|_| ConfigError::InvalidValue {
            key: OWN_KEY_ID.to_owned(),
        })
    })?;
    let secret = crate::read_secret_file(source, OWN_KEY_FILE)?;
    Ok(Some((key_id, secret)))
}

fn parse_entry(entry: &str) -> Option<(String, u32, String)> {
    let (service, rest) = entry.split_once(':')?;
    let (key_id, path) = rest.split_once(':')?;
    let key_id = key_id.parse().ok()?;
    let named = !service.is_empty() && !path.is_empty();
    named.then(|| (service.to_owned(), key_id, path.to_owned()))
}

fn load(service: &str, key_id: u32, path: &Path) -> Result<PeerKey, ConfigError> {
    let text = std::fs::read_to_string(path).map_err(|_| ConfigError::SecretUnreadable {
        key: KEY.to_owned(),
    })?;
    Ok(PeerKey {
        service: service.to_owned(),
        key_id,
        secret: Secret::new(text.trim_end().to_owned()),
    })
}

#[cfg(test)]
mod tests {
    use super::read_peer_keys;
    use crate::{ConfigError, MapSource};

    #[test]
    fn no_setting_means_no_peers() {
        assert_eq!(
            read_peer_keys(&MapSource::default()).map(|keys| keys.len()),
            Ok(0)
        );
    }

    fn is_refused(entry: &str) -> bool {
        let source = MapSource::default().with("ELIBRARY_SERVICE_CALLERS", entry);
        matches!(
            read_peer_keys(&source),
            Err(ConfigError::InvalidValue { .. })
        )
    }

    #[test]
    fn malformed_entries_are_refused() {
        let bad = ["gateway", "gateway:x:/p", ":1:/p", "gateway:1:"];
        let accepted: Vec<&str> = bad.into_iter().filter(|entry| !is_refused(entry)).collect();
        assert!(accepted.is_empty(), "{accepted:?}");
    }

    #[test]
    fn a_missing_file_is_unreadable() {
        let source =
            MapSource::default().with("ELIBRARY_SERVICE_CALLERS", "gateway:1:/nonexistent/key");
        assert!(matches!(
            read_peer_keys(&source),
            Err(ConfigError::SecretUnreadable { .. })
        ));
    }
}
