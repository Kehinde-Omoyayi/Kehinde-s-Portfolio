from datetime import datetime, timezone as dt_timezone
from types import SimpleNamespace

from .models import Project, Dashboard, Certificate, Publication, Recommendation

ACTIVITY_TYPES = [
    ("project", "New project"),
    ("dashboard", "New dashboard"),
    ("certificate", "New certificate"),
    ("research", "New research paper"),
    ("recommendation", "New recommendation"),
]

ACCENT_VAR = {
    "project": "--brand-blue",
    "dashboard": "--brand-emerald",
    "certificate": "--brand-amber",
    "research": "--brand-cyan",
    "recommendation": "--brand-pink",
}

_TYPE_DISPLAY = dict(ACTIVITY_TYPES)
_MIN_DATE = datetime.min.replace(tzinfo=dt_timezone.utc)


def _entry(activity_type, title, url, date, image):
    return SimpleNamespace(
        activity_type=activity_type,
        title=title,
        url=url or "",
        created_at=date,
        image=image if image else None,
        accent_var=ACCENT_VAR[activity_type],
        type_display=_TYPE_DISPLAY[activity_type],
    )


def get_activity_feed(activity_type=None):
    """
    Returns a list of SimpleNamespace entries, newest first.
    Pass activity_type ("project"/"dashboard"/"certificate"/"research"/
    "recommendation") to filter to just that type.
    """
    entries = []

    if activity_type in (None, "project"):
        for p in Project.objects.filter(status="published"):
            entries.append(_entry(
                "project", p.name, p.get_absolute_url(), p.created_at, p.cover_image,
            ))

    if activity_type in (None, "dashboard"):
        for d in Dashboard.objects.filter(is_published=True):
            entries.append(_entry(
                "dashboard", d.title, d.get_absolute_url(), d.created_at, d.thumbnail,
            ))

    if activity_type in (None, "certificate"):
        for c in Certificate.objects.filter(is_visible=True):
            # Certificate has no detail page / slug field — link out to the
            # issuing credential instead, if one was provided.
            date = c.date_issued
            if date is not None:
                date = datetime.combine(date, datetime.min.time(), tzinfo=dt_timezone.utc)
            entries.append(_entry(
                "certificate", c.title, c.credential_url, date, c.image,
            ))

    if activity_type in (None, "research"):
        for r in Publication.objects.filter(is_published=True):
            entries.append(_entry(
                "research", r.title, r.get_absolute_url(), r.published_at, r.cover_image,
            ))

    if activity_type in (None, "recommendation"):
        for rec in Recommendation.objects.filter(is_visible=True):
            title = rec.name
            if rec.title_and_company:
                title = f"{rec.name} — {rec.title_and_company}"
            entries.append(_entry(
                "recommendation", title, rec.url, rec.created_at, rec.photo,
            ))

    entries.sort(key=lambda e: e.created_at or _MIN_DATE, reverse=True)
    return entries