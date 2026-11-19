//! Gate Q10: every external crate a workspace crate depends on has an APPROVED row in the
//! dependency register (`planning/04-architecture/dependency-policy.md`, D-17, I-27).

use std::collections::BTreeSet;

/// Names with no APPROVED entry in `register`.
#[must_use]
pub fn unapproved(register: &str, dependencies: &BTreeSet<String>) -> Vec<String> {
    dependencies
        .iter()
        .filter(|name| !is_approved(register, name))
        .cloned()
        .collect()
}

// why: "`name` (APPROVED ...)" - the word must follow the crate's own mention, up to the next
// backticked name, so an approval of one crate never covers its neighbour in the same row.
fn is_approved(register: &str, name: &str) -> bool {
    let marker = format!("`{name}`");
    register.lines().any(|line| line_approves(line, &marker))
}

fn line_approves(line: &str, marker: &str) -> bool {
    line.match_indices(marker)
        .filter_map(|(at, _)| line.get(at + marker.len()..))
        .any(is_followed_by_approval)
}

fn is_followed_by_approval(rest: &str) -> bool {
    rest.split('`')
        .next()
        .is_some_and(|segment| segment.contains("APPROVED"))
}

#[cfg(test)]
mod tests {
    use super::*;

    const REGISTER: &str = "| Time | `time` (APPROVED D-62, in use) |\n\
| Serialization | `serde` (APPROVED D-62), `serde_json` |\n\
| Crypto | `argon2`, `sha2` | proposed |";

    fn names(list: &[&str]) -> BTreeSet<String> {
        list.iter().map(|name| (*name).to_owned()).collect()
    }

    #[test]
    fn approved_rows_pass_and_neighbours_do_not_inherit() {
        assert_eq!(
            unapproved(REGISTER, &names(&["time", "serde"])),
            Vec::<String>::new()
        );
        assert_eq!(
            unapproved(REGISTER, &names(&["serde_json", "argon2", "tokio"])),
            vec!["argon2", "serde_json", "tokio"]
        );
    }
}
