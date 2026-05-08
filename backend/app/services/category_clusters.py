"""Hardcoded category similarity clusters for recommendation and discovery."""

from supabase import Client

from app.repositories import category as _category_repo

CATEGORY_CLUSTERS: dict[str, list[str]] = {
    "active":   ["Sports", "Health & Wellness", "Outdoor"],
    "creative": ["Music", "Arts & Culture", "Film & Media"],
    "social":   ["Nightlife", "Community", "Food & Drink", "Family"],
    "learning": ["Technology", "Education", "Business"],
    "leisure":  ["Gaming", "Travel"],
}

# Inverted index: category name → cluster name (built once at import time)
_NAME_TO_CLUSTER: dict[str, str] = {
    name: cluster
    for cluster, names in CATEGORY_CLUSTERS.items()
    for name in names
}


def expand_category_ids(db: Client, exact_ids: set[str]) -> set[str]:
    """Return exact_ids plus all category IDs from the same cluster(s).

    Fetches category names from the DB only for the exact IDs so the
    cluster lookup stays O(|exact_ids|), not O(all categories).
    """
    if not exact_ids:
        return exact_ids

    name_rows = _category_repo.get_categories_by_ids(db, list(exact_ids))
    exact_names: set[str] = {row["name"] for row in name_rows}

    touched_clusters: set[str] = set()
    for name in exact_names:
        cluster = _NAME_TO_CLUSTER.get(name)
        if cluster:
            touched_clusters.add(cluster)

    if not touched_clusters:
        return exact_ids

    similar_names: set[str] = set()
    for cluster in touched_clusters:
        similar_names.update(CATEGORY_CLUSTERS[cluster])
    similar_names -= exact_names

    if not similar_names:
        return exact_ids

    similar_rows = _category_repo.get_categories_by_names(db, list(similar_names))
    return exact_ids | {row["id"] for row in similar_rows}
