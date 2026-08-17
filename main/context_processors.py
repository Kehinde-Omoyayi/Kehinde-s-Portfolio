from django.conf import settings

from .models import (
    SiteProfile, Connect_Link, Tools,
    Project, Dashboard, Certificate, Publication, Dataset,
)

def site_globals(request):
    profile = (
        SiteProfile.objects
        .select_related("active_cv")
        .prefetch_related("role_titles", "highlights")
        .first()
    )

    return {
        "site_profile": profile,
        "connect_links": Connect_Link.objects.filter(is_visible=True),
        "nav_tools": Tools.objects.filter(is_visible=True),
        "site_stats": {
            "projects": Project.objects.filter(status="published").count(),
            "dashboards": Dashboard.objects.filter(is_published=True).count(),
            "research": Publication.objects.filter(is_published=True).count(),
            "certificates": Certificate.objects.filter(is_visible=True).count(),
            "technologies": Tools.objects.filter(is_visible=True).count(),
        },
        "email_configured": settings.EMAIL_IS_CONFIGURED,
    }

