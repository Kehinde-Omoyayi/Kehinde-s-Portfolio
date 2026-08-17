from main.models import (
    Category, Tools, Connect_Link, CVDocument, Dataset,
    Certificate, Recommendation, Publication,
    Open_Roles, Roles, AboutStat, AboutPillar, SignatureOutcome,
)

SECTIONS = {
    # ── Content tags ──────────────────────────────────────────────
    "categories": {
        "model": Category,
        "label": "Categories",
        "singular": "Category",
        "fields": ["name"],
        "list_columns": [("name", "Name")],
        "icon": "🏷️",
        "group": "Content Tags",
    },
    "technologies": {
        "model": Tools,
        "label": "Tools & Technologies",
        "singular": "Tool",
        "fields": ["name", "icon_image", "is_visible"],
        "list_columns": [("name", "Name"), ("is_visible", "Visible")],
        "icon": "🧰",
        "group": "Content Tags",
    },

    # ── Connect ───────────────────────────────────────────────────
    "connect-links": {
        "model": Connect_Link,
        "label": "Connect Links",
        "singular": "Connect Link",
        "fields": ["platform", "url_or_handle", "is_visible"],
        "list_columns": [("platform", "Platform"), ("url_or_handle", "Link"), ("is_visible", "Visible")],
        "icon": "🔗",
        "group": "Site-wide",
    },

    # ── CV & Downloads ────────────────────────────────────────────
    "cv": {
        "model": CVDocument,
        "label": "CV / Resume Files",
        "singular": "CV File",
        "fields": ["title", "file", "is_public"],
        "list_columns": [("title", "Title"), ("is_public", "Public")],
        "icon": "📄",
        "group": "CV & Downloads",
    },
    "downloads": {
        "model": Dataset,
        "label": "Datasets & Reports",
        "singular": "File",
        "fields": ["title", "description", "kind", "file", "related_project", "is_public"],
        "list_columns": [("title", "Title"), ("kind", "Kind"), ("is_public", "Public")],
        "icon": "📊",
        "group": "CV & Downloads",
    },

    # ── Credibility ────────────────────────────────────────────────
    "certificates": {
        "model": Certificate,
        "label": "Certificates",
        "singular": "Certificate",
        "fields": ["title", "issuing_organization", "image", "credential_url", "description",
                   "date_issued", "is_visible", "order"],
        "list_columns": [("title", "Title"), ("issuing_organization", "Issuer"), ("is_visible", "Visible")],
        "icon": "🎓",
        "group": "Credibility",
    },
    "recommendations": {
        "model": Recommendation,
        "label": "Recommendations",
        "singular": "Recommendation",
        "fields": ["name", "title_and_company", "photo", "message", "url", "is_visible", "order"],
        "list_columns": [("name", "Name"), ("title_and_company", "Title / Company"), ("is_visible", "Visible")],
        "icon": "💬",
        "group": "Credibility",
    },

    # ── Writing ────────────────────────────────────────────────────
    "research": {
        "model": Publication,
        "label": "Research / Publications",
        "singular": "Publication",
        "fields": ["title", "authors", "abstract", "cover_image", "pdf_file", "external_url",
                   "categories", "publication_year", "is_published", "published_at"],
        "list_columns": [("title", "Title"), ("publication_year", "Year"), ("is_published", "Published")],
        "icon": "🔬",
        "group": "Writing",
    },

    # ── Profile extras ─────────────────────────────────────────────
    "open-roles": {
        "model": Open_Roles,
        "label": "Open Roles",
        "singular": "Role",
        "fields": ["roles"],
        "list_columns": [("roles", "Role")],
        "icon": "🎯",
        "group": "Profile",
    },
    "job-titles": {
        "model": Roles,
        "label": "Job Titles / Role Labels",
        "singular": "Title",
        "fields": ["roles"],
        "list_columns": [("roles", "Title")],
        "icon": "🏷",
        "group": "Profile",
    },
    "about-stats": {
        "model": AboutStat,
        "label": "About Stats",
        "singular": "Stat",
        "fields": ["value", "suffix", "label", "order"],
        "list_columns": [("value", "Value"), ("suffix", "Suffix"), ("label", "Label"), ("order", "Order")],
        "icon": "📈",
        "group": "Profile",
    },
    "about-pillars": {
        "model": AboutPillar,
        "label": "About Pillars",
        "singular": "Pillar",
        "fields": ["title", "description", "order"],
        "list_columns": [("title", "Title"), ("order", "Order")],
        "icon": "🏛",
        "group": "Profile",
    },
    "signature-outcomes": {
        "model": SignatureOutcome,
        "label": "Signature Outcomes",
        "singular": "Outcome",
        "fields": ["stat", "title", "detail", "order"],
        "list_columns": [("stat", "Stat"), ("title", "Title"), ("order", "Order")],
        "icon": "⭐",
        "group": "Profile",
    },
}