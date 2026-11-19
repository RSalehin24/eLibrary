//! Gate Q6: which workspace crates may depend on which (workspace layout rules).

use std::collections::BTreeMap;

/// Crate name to the names of workspace crates it depends on.
pub type Edges = BTreeMap<String, Vec<String>>;

const CONTRACTS_IDS: &str = "contracts-ids";
const CONTRACTS_HTTP: &str = "contracts-http";

/// Every forbidden edge, as a readable line. Empty when the graph is clean.
#[must_use]
pub fn violations(edges: &Edges) -> Vec<String> {
    edges
        .iter()
        .flat_map(|(from, targets)| targets.iter().map(move |to| (from, to)))
        .filter(|(from, to)| !is_allowed(from, to))
        .map(|(from, to)| format!("{from} must not depend on {to}"))
        .collect()
}

fn is_allowed(from: &str, to: &str) -> bool {
    match Layer::of(from) {
        Layer::Domain => to == CONTRACTS_IDS || Layer::of(to) == Layer::Domain,
        // why: shared HTTP wire types (error envelope, scopes) have one home; logged as I-26.
        Layer::Contracts => to == CONTRACTS_IDS || to == CONTRACTS_HTTP,
        // why: platform crates build on each other (obs and db use config); logged as I-25.
        Layer::Platform => matches!(Layer::of(to), Layer::Platform | Layer::Contracts),
        Layer::Service => Layer::of(to) != Layer::Service,
        Layer::Tooling => true,
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Layer {
    Domain,
    Contracts,
    Platform,
    Service,
    Tooling,
}

impl Layer {
    fn of(name: &str) -> Self {
        match name.split('-').next() {
            Some("domain") => Self::Domain,
            Some("contracts") => Self::Contracts,
            Some("platform") => Self::Platform,
            Some("svc") => Self::Service,
            _ => Self::Tooling,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn edge_list(targets: &[&str]) -> Vec<String> {
        targets.iter().map(|target| (*target).to_owned()).collect()
    }

    fn edges(pairs: &[(&str, &[&str])]) -> Edges {
        pairs
            .iter()
            .map(|(from, targets)| ((*from).to_owned(), edge_list(targets)))
            .collect()
    }

    #[test]
    fn service_to_service_is_forbidden() {
        let found = violations(&edges(&[("svc-catalog", &["svc-identity", "platform-db"])]));
        assert_eq!(found, vec!["svc-catalog must not depend on svc-identity"]);
    }

    #[test]
    fn domain_must_not_touch_platform_or_services() {
        let found = violations(&edges(&[(
            "domain-text",
            &["platform-time", "svc-x", "domain-access"],
        )]));
        assert_eq!(found.len(), 2);
    }

    #[test]
    fn allowed_edges_pass() {
        let graph = edges(&[
            (
                "svc-identity",
                &["platform-db", "domain-text", "contracts-ids"],
            ),
            ("platform-obs", &["platform-config"]),
            ("contracts-events", &["contracts-ids"]),
            ("domain-access", &["contracts-ids", "domain-text"]),
        ]);
        assert_eq!(violations(&graph), Vec::<String>::new());
    }

    #[test]
    fn contracts_depend_only_on_ids_and_http() {
        let found = violations(&edges(&[(
            "contracts-catalog",
            &["domain-text", "contracts-events"],
        )]));
        assert_eq!(found.len(), 2);
        let allowed = edges(&[("contracts-catalog", &["contracts-ids", "contracts-http"])]);
        assert_eq!(violations(&allowed), Vec::<String>::new());
    }
}
