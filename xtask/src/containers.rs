//! Gate Q11: container hardening rules checked on the resolved Compose configuration
//! (`docker compose config --format json`): INV-PLT-001, INV-PLT-004, INV-PLT-016.

use serde_json::Value;

const SECRET_WORDS: [&str; 4] = ["PASSWORD", "SECRET", "TOKEN", "KEY"];
const PUBLISHING_SERVICE: &str = "caddy";

/// Every broken rule as a readable line; empty when the configuration is clean.
#[must_use]
pub fn violations(config: &Value) -> Vec<String> {
    let mut found = Vec::new();
    let services = config.get("services").and_then(Value::as_object);
    for (name, service) in services.into_iter().flatten() {
        found.extend(service_violations(name, service));
    }
    found.extend(secret_violations(config));
    found
}

fn service_violations(name: &str, service: &Value) -> Vec<String> {
    let mut found = Vec::new();
    let is_one_shot = service.get("restart").and_then(Value::as_str) == Some("no");
    if has_ports(service) && name != PUBLISHING_SERVICE {
        found.push(format!(
            "{name} publishes ports; only {PUBLISHING_SERVICE} may"
        ));
    }
    if !is_positive(service.get("mem_limit")) {
        found.push(format!("{name} has no memory limit"));
    }
    if service.get("read_only") != Some(&Value::Bool(true)) {
        found.push(format!("{name} does not have a read-only root filesystem"));
    }
    if !drops_all_capabilities(service) {
        found.push(format!("{name} does not drop all capabilities"));
    }
    if !is_one_shot && service.get("restart").is_none() {
        found.push(format!("{name} has no restart policy"));
    }
    found.extend(plain_secret_environment(name, service));
    found
}

fn has_ports(service: &Value) -> bool {
    service
        .get("ports")
        .and_then(Value::as_array)
        .is_some_and(|ports| !ports.is_empty())
}

// why: `docker compose config` renders byte values as numeric strings, tests use numbers.
fn is_positive(value: Option<&Value>) -> bool {
    let bytes = match value {
        Some(Value::String(text)) => text.parse::<i64>().ok(),
        Some(number) => number.as_i64(),
        None => None,
    };
    bytes.is_some_and(|bytes| bytes > 0)
}

fn drops_all_capabilities(service: &Value) -> bool {
    service
        .get("cap_drop")
        .and_then(Value::as_array)
        .is_some_and(|drops| drops.iter().any(|drop| drop.as_str() == Some("ALL")))
}

// why: secrets reach containers as files (*_FILE paths), never as plain environment values.
fn plain_secret_environment(name: &str, service: &Value) -> Vec<String> {
    let environment = service.get("environment").and_then(Value::as_object);
    environment
        .into_iter()
        .flatten()
        .map(|(key, _)| key)
        .filter(|key| SECRET_WORDS.iter().any(|word| key.contains(word)) && !key.ends_with("_FILE"))
        .map(|key| format!("{name} sets {key} in the environment; use a secret file"))
        .collect()
}

fn secret_violations(config: &Value) -> Vec<String> {
    let secrets = config.get("secrets").and_then(Value::as_object);
    secrets
        .into_iter()
        .flatten()
        .filter(|(_, secret)| secret.get("file").is_none())
        .map(|(name, _)| format!("secret {name} is not a file"))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn hardened() -> Value {
        json!({"mem_limit": 1000, "read_only": true, "cap_drop": ["ALL"], "restart": "unless-stopped"})
    }

    #[test]
    fn a_hardened_stack_is_clean() {
        let config = json!({"services": {"caddy": {"ports": [{}], "mem_limit": 1000, "read_only": true,
            "cap_drop": ["ALL"], "restart": "unless-stopped"}, "app": hardened()}, "secrets": {"s": {"file": "x"}}});
        assert_eq!(violations(&config), Vec::<String>::new());
    }

    #[test]
    fn each_rule_is_enforced() {
        let config = json!({"services": {"app": {"ports": [{}], "environment": {"DB_PASSWORD": "x", "DB_PASSWORD_FILE": "y"}}},
            "secrets": {"s": {"environment": "X"}}});
        let found = violations(&config).join("\n");
        let needles = [
            "publishes ports",
            "no memory limit",
            "read-only",
            "drop all",
            "no restart",
            "DB_PASSWORD in",
            "secret s",
        ];
        let missing: Vec<&str> = needles
            .into_iter()
            .filter(|needle| !found.contains(needle))
            .collect();
        assert_eq!(missing, Vec::<&str>::new(), "in:\n{found}");
        assert!(!found.contains("DB_PASSWORD_FILE in"));
    }
}
