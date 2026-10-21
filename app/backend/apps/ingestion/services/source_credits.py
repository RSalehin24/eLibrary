"""Corrections supported by explicit source credits, never fuzzy person matching."""

from collections.abc import Iterable, Mapping

from apps.common.text import normalize_catalog_text

VERIFIED_CREDIT_NAMES = {
    "বিদেশি ছবি অবলম্বনে কোলায বনবীর আহমেদ বিতর": "বনবীর আহমেদ",
}
VERIFIED_ROLE_ALIASES = {"সাঈম শামস": "সাঈম শামস্"}
NON_CREDIT_PHRASES = {"তাড়া দিচ্ছেন"}


def credit_identity(name: str) -> str:
    canonical = VERIFIED_ROLE_ALIASES.get(name, name)
    return str(normalize_catalog_text(canonical))


def curate_explicit_credits(
    entries: Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    credits = [dict(entry) for entry in entries]
    publishers = {entry["name"] for entry in credits if entry["role"] == "publisher"}
    result = []
    for entry in credits:
        name, role = entry["name"], entry["role"]
        if role == "publisher" and name in NON_CREDIT_PHRASES:
            continue
        if role == "cover_artist":
            name = VERIFIED_CREDIT_NAMES.get(name, name)
        # Prose often repeats an already explicit publisher with this prefix.
        if role == "publisher" and name.startswith("এর জনাব "):
            candidate = name.removeprefix("এর জনাব ")
            if candidate in publishers:
                name = candidate
        result.append({**entry, "name": name})
    return result


def repairable_credit_names() -> set[str]:
    return {
        *VERIFIED_CREDIT_NAMES,
        *VERIFIED_ROLE_ALIASES,
        *NON_CREDIT_PHRASES,
        "এর জনাব ফরিদ আহমেদ",
    }
