use std::collections::BTreeMap;

/// Where settings come from. Injected so tests never read the real environment.
pub trait ConfigSource {
    fn get(&self, key: &str) -> Option<String>;

    /// Every key that starts with `prefix`, used to reject unknown settings.
    fn keys_with_prefix(&self, prefix: &str) -> Vec<String>;
}

/// Process environment.
#[derive(Debug, Clone, Copy, Default)]
pub struct EnvSource;

impl ConfigSource for EnvSource {
    fn get(&self, key: &str) -> Option<String> {
        std::env::var(key).ok()
    }

    fn keys_with_prefix(&self, prefix: &str) -> Vec<String> {
        std::env::vars_os()
            .filter_map(|(key, _)| key.into_string().ok())
            .filter(|key| key.starts_with(prefix))
            .collect()
    }
}

/// In-memory settings for tests.
#[derive(Debug, Clone, Default)]
pub struct MapSource(BTreeMap<String, String>);

impl MapSource {
    #[must_use]
    pub fn with(mut self, key: &str, value: &str) -> Self {
        self.0.insert(key.to_owned(), value.to_owned());
        self
    }
}

impl ConfigSource for MapSource {
    fn get(&self, key: &str) -> Option<String> {
        self.0.get(key).cloned()
    }

    fn keys_with_prefix(&self, prefix: &str) -> Vec<String> {
        self.0
            .keys()
            .filter(|key| key.starts_with(prefix))
            .cloned()
            .collect()
    }
}
