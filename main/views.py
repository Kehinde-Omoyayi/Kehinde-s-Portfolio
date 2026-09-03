from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.http import JsonResponse, Http404
from django.db.models import Q
from django.views.decorators.http import require_GET

from .activity import get_activity_feed, ACTIVITY_TYPES
from .models import (
    Project, Dashboard, Certificate, Recommendation, Tools, Publication,
    Category, SiteProfile, Connect_Link, Currently_Focused, Open_Roles,
    SignatureOutcome, AboutPillar, AboutStat, DownloadLog, PageView,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _get_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")


def _log_pageview(request):
    try:
        PageView.objects.create(path=request.path, ip_address=_get_ip(request))
    except Exception:
        pass


def _get_site_profile():
    return (
        SiteProfile.objects
        .select_related("active_cv")
        .prefetch_related("highlights", "role_titles")
        .first()
    )


def _absolute_image_url(request, image):
    if not image:
        return None
    try:
        return request.build_absolute_uri(image.url)
    except (AttributeError, ValueError):
        return None


def _seo_description(text, fallback):
    if not text:
        return fallback
    text = " ".join(str(text).split())
    return text[:200] + "..." if len(text) > 200 else text


def _seo_context(
    request,
    site_profile=None,
    title=None,
    description=None,
    image=None,
    image_alt=None,
):
    site_profile = site_profile or _get_site_profile()

    profile_name = (
        site_profile.full_name
        if site_profile
        else "Kehinde Omoyayi"
    )

    default_description = (
        site_profile.short_bio
        if site_profile and site_profile.short_bio
        else "Turning data into actionable insights, building intelligent solutions and creating impact."
    )

    # Object-specific image first; profile picture is the fallback.
    seo_image = _absolute_image_url(request, image)

    if not seo_image and site_profile:
        seo_image = _absolute_image_url(
            request,
            site_profile.profile_picture,
        )

    return {
        "site_profile": site_profile,
        "seo_url": request.build_absolute_uri(),
        "seo_title": title or f"{profile_name} | Data Analyst & Business Intelligence",
        "seo_description": _seo_description(
            description,
            default_description,
        ),
        "seo_image": seo_image,
        "seo_image_alt": image_alt or profile_name,
    }


def _base_context(request, site_profile=None, **seo_kwargs):
    site_profile = site_profile or _get_site_profile()

    return {
        "site_profile": site_profile,
        "social_links": Connect_Link.objects.filter(is_visible=True),
        **_seo_context(request, site_profile, **seo_kwargs),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Home
# ──────────────────────────────────────────────────────────────────────────────

def home_page(request):
    _log_pageview(request)
    site_profile = _get_site_profile()

    profile_name = (
        site_profile.full_name
        if site_profile
        else "Kehinde Omoyayi"
    )

    context = _base_context(
        request,
        site_profile,
        title=f"{profile_name} | Data Analyst & Business Intelligence",
        description=site_profile.short_bio if site_profile else None,
        image=site_profile.profile_picture if site_profile else None,
        image_alt=profile_name,
    )

    context.update({
        "open_roles": Open_Roles.objects.all(),
        "currently_focused": Currently_Focused.objects.all(),
        "stat_projects": Project.objects.filter(status="published").count(),
        "stat_dashboards": Dashboard.objects.filter(is_published=True).count(),
        "stat_research": Publication.objects.filter(is_published=True).count(),
        "stat_technologies": Tools.objects.filter(is_visible=True).count(),
        "stat_certificates": Certificate.objects.filter(is_visible=True).count(),
        "certificates": Certificate.objects.all(),
        "featured_projects": (
            Project.objects
            .filter(status="published", is_featured=True)
            .prefetch_related("categories", "technologies", "links")
            .order_by("order", "-created_at")[:6]
        ),
        "featured_dashboards": (
            Dashboard.objects
            .filter(is_published=True, is_featured=True)
            .prefetch_related("metrics", "categories", "technologies")
            .order_by("order", "-created_at")[:3]
        ),
        "featured_research": (
            Publication.objects
            .filter(is_published=True)
            .prefetch_related("categories")
            .order_by("-published_at")[:3]
        ),
        "latest_activity": get_activity_feed()[:6],
        "tools": Tools.objects.filter(is_visible=True),
        "recommendations": Recommendation.objects.filter(is_visible=True)[:6],
        "motion_items": [
            {"image_url": p.cover_image.url, "caption": p.name}
            for p in Project.objects.filter(is_featured=True).exclude(cover_image="")
        ],
    })

    return render(request, "home/index.html", context)


# ──────────────────────────────────────────────────────────────────────────────
# Projects
# ──────────────────────────────────────────────────────────────────────────────

def project_list(request):
    _log_pageview(request)
    site_profile = _get_site_profile()

    projects = Project.objects.filter(status="published")
    category_slug = request.GET.get("category")

    if category_slug:
        projects = projects.filter(categories__slug=category_slug)

    page_obj = Paginator(projects, 9).get_page(
        request.GET.get("page")
    )

    context = _base_context(
        request,
        site_profile,
        title=f"Projects | {site_profile.full_name}" if site_profile else "Projects | Kehinde Omoyayi",
        description="Explore data analytics, business intelligence and engineering projects by Kehinde Omoyayi.",
        image=site_profile.profile_picture if site_profile else None,
    )

    context.update({
        "page_obj": page_obj,
        "categories": Category.objects.filter(
            projects__isnull=False
        ).distinct(),
        "selected_category": category_slug,
    })

    return render(
        request,
        "portfolio/project_list.html",
        context,
    )


def project_detail(request, slug):
    _log_pageview(request)

    project = get_object_or_404(
        Project,
        slug=slug,
        status="published",
    )

    site_profile = _get_site_profile()

    context = _base_context(
        request,
        site_profile,
        title=f"{project.name} | {site_profile.full_name}" if site_profile else f"{project.name} | Kehinde Omoyayi",
        description=project.summary or project.description,
        image=project.cover_image,
        image_alt=project.name,
    )

    context["project"] = project

    return render(
        request,
        "portfolio/project_detail.html",
        context,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Dashboards
# ──────────────────────────────────────────────────────────────────────────────

def dashboard_list(request):
    _log_pageview(request)
    site_profile = _get_site_profile()

    context = _base_context(
        request,
        site_profile,
        title=f"Dashboards | {site_profile.full_name}" if site_profile else "Dashboards | Kehinde Omoyayi",
        description="Interactive data analytics and business intelligence dashboards created by Kehinde Omoyayi.",
        image=site_profile.profile_picture if site_profile else None,
    )

    context["dashboards"] = Dashboard.objects.filter(
        is_published=True
    )

    return render(
        request,
        "portfolio/dashboard_list.html",
        context,
    )


def dashboard_detail(request, slug):
    _log_pageview(request)

    dashboard = get_object_or_404(
        Dashboard,
        slug=slug,
        is_published=True,
    )

    site_profile = _get_site_profile()

    context = _base_context(
        request,
        site_profile,
        title=f"{dashboard.title} | {site_profile.full_name}" if site_profile else f"{dashboard.title} | Kehinde Omoyayi",
        description=dashboard.description or f"Interactive dashboard created by {site_profile.full_name if site_profile else 'Kehinde Omoyayi'}.",
        image=dashboard.thumbnail,
        image_alt=dashboard.title,
    )

    context["dashboard"] = dashboard

    return render(
        request,
        "portfolio/dashboard_detail.html",
        context,
    )


# ──────────────────────────────────────────────────────────────────────────────
# CV
# ──────────────────────────────────────────────────────────────────────────────

def cv_downloads(request):
    _log_pageview(request)

    site_profile = _get_site_profile()
    profile_cv = site_profile.active_cv if site_profile else None

    context = _base_context(
        request,
        site_profile,
        title=f"Curriculum Vitae | {site_profile.full_name}" if site_profile else "Curriculum Vitae | Kehinde Omoyayi",
        description=(
            f"View or download the CV of {site_profile.full_name}."
            if site_profile
            else "View or download the CV of Kehinde Omoyayi."
        ),
        image=site_profile.profile_picture if site_profile else None,
    )

    context["profile_cv"] = profile_cv

    return render(
        request,
        "portfolio/cv.html",
        context,
    )


def cv_download_tracked(request):
    site_profile = (
        SiteProfile.objects
        .select_related("active_cv")
        .first()
    )

    if not site_profile or not site_profile.active_cv:
        raise Http404("No CV available")

    cv = site_profile.active_cv

    try:
        DownloadLog.objects.create(
            file_type="cv",
            object_id=cv.pk,
            object_title=cv.title,
            ip_address=_get_ip(request),
            user_agent=request.META.get(
                "HTTP_USER_AGENT",
                "",
            )[:400],
        )
    except Exception:
        pass

    if (
        request.headers.get(
            "Accept",
            "",
        ).startswith("application/json")
        or request.GET.get("track") == "1"
    ):
        return JsonResponse({"ok": True})

    return redirect(cv.file.url)


def cv_track_ping(request):
    site_profile = (
        SiteProfile.objects
        .select_related("active_cv")
        .first()
    )

    if site_profile and site_profile.active_cv:
        cv = site_profile.active_cv

        try:
            DownloadLog.objects.create(
                file_type="cv",
                object_id=cv.pk,
                object_title=cv.title,
                ip_address=_get_ip(request),
                user_agent=request.META.get(
                    "HTTP_USER_AGENT",
                    "",
                )[:400],
            )
        except Exception:
            pass

    return JsonResponse({"ok": True})


# ──────────────────────────────────────────────────────────────────────────────
# Project PDF
# ──────────────────────────────────────────────────────────────────────────────

def project_pdf_download(request, pk):
    project = get_object_or_404(
        Project,
        pk=pk,
        status="published",
    )

    if not project.pdf_report:
        raise Http404("No PDF for this project")

    try:
        DownloadLog.objects.create(
            file_type="project_pdf",
            object_id=project.pk,
            object_title=project.name,
            ip_address=_get_ip(request),
            user_agent=request.META.get(
                "HTTP_USER_AGENT",
                "",
            )[:400],
        )
    except Exception:
        pass

    if (
        request.headers.get(
            "Accept",
            "",
        ).startswith("application/json")
        or request.GET.get("track") == "1"
    ):
        return JsonResponse({"ok": True})

    return redirect(project.pdf_report.url)


def project_pdf_track_ping(request, pk):
    project = get_object_or_404(
        Project,
        pk=pk,
        status="published",
    )

    if project.pdf_report:
        try:
            DownloadLog.objects.create(
                file_type="project_pdf",
                object_id=project.pk,
                object_title=project.name,
                ip_address=_get_ip(request),
                user_agent=request.META.get(
                    "HTTP_USER_AGENT",
                    "",
                )[:400],
            )
        except Exception:
            pass

    return JsonResponse({"ok": True})


# ──────────────────────────────────────────────────────────────────────────────
# Certificates
# ──────────────────────────────────────────────────────────────────────────────

def certificate_list(request):
    _log_pageview(request)
    site_profile = _get_site_profile()

    context = _base_context(
        request,
        site_profile,
        title=f"Certificates | {site_profile.full_name}" if site_profile else "Certificates | Kehinde Omoyayi",
        description="Certifications and professional learning achievements of Kehinde Omoyayi.",
        image=site_profile.profile_picture if site_profile else None,
    )

    context["certificates"] = Certificate.objects.filter(
        is_visible=True
    )

    return render(
        request,
        "portfolio/certificates.html",
        context,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Recommendations
# ──────────────────────────────────────────────────────────────────────────────

def recommendation_list(request):
    _log_pageview(request)
    site_profile = _get_site_profile()

    context = _base_context(
        request,
        site_profile,
        title=f"Recommendations | {site_profile.full_name}" if site_profile else "Recommendations | Kehinde Omoyayi",
        description="Professional recommendations and testimonials for Kehinde Omoyayi.",
        image=site_profile.profile_picture if site_profile else None,
    )

    context["recommendations"] = Recommendation.objects.filter(
        is_visible=True
    )

    return render(
        request,
        "portfolio/recommendations.html",
        context,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Activity
# ──────────────────────────────────────────────────────────────────────────────

def activity_list(request):
    _log_pageview(request)
    site_profile = _get_site_profile()

    activity_type = request.GET.get("type")

    if activity_type not in dict(ACTIVITY_TYPES):
        activity_type = None

    page_obj = Paginator(
        get_activity_feed(activity_type),
        8,
    ).get_page(
        request.GET.get("page")
    )

    context = _base_context(
        request,
        site_profile,
        title=f"Recent Activity | {site_profile.full_name}" if site_profile else "Recent Activity | Kehinde Omoyayi",
        description="Latest projects, dashboards, research, certificates and professional updates.",
        image=site_profile.profile_picture if site_profile else None,
    )

    context.update({
        "page_obj": page_obj,
        "activity_types": ACTIVITY_TYPES,
        "selected_type": activity_type,
    })

    return render(
        request,
        "portfolio/activity_list.html",
        context,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Research
# ──────────────────────────────────────────────────────────────────────────────

def research_list(request):
    _log_pageview(request)
    site_profile = _get_site_profile()

    publication = Publication.objects.filter(
        is_published=True
    )

    category_slug = request.GET.get("category")

    if category_slug:
        publication = publication.filter(
            categories__slug=category_slug
        )

    page_obj = Paginator(
        publication,
        9,
    ).get_page(
        request.GET.get("page")
    )

    context = _base_context(
        request,
        site_profile,
        title=f"Research | {site_profile.full_name}" if site_profile else "Research | Kehinde Omoyayi",
        description="Research publications and academic projects by Kehinde Omoyayi.",
        image=site_profile.profile_picture if site_profile else None,
    )

    context.update({
        "page_obj": page_obj,
        "categories": Category.objects.filter(
            publications__isnull=False
        ).distinct(),
        "selected_category": category_slug,
    })

    return render(
        request,
        "portfolio/research_list.html",
        context,
    )


def research_detail(request, slug):
    _log_pageview(request)

    publication = get_object_or_404(
        Publication,
        slug=slug,
        is_published=True,
    )

    site_profile = _get_site_profile()

    context = _base_context(
        request,
        site_profile,
        title=f"{publication.title} | {site_profile.full_name}" if site_profile else f"{publication.title} | Kehinde Omoyayi",
        description=publication.abstract or "Research publication by Kehinde Omoyayi.",
        image=publication.cover_image,
        image_alt=publication.title,
    )

    context["publication"] = publication

    return render(
        request,
        "portfolio/research_detail.html",
        context,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Contact / About
# ──────────────────────────────────────────────────────────────────────────────

def contact(request):
    _log_pageview(request)
    site_profile = _get_site_profile()

    context = _base_context(
        request,
        site_profile,
        title=f"About {site_profile.full_name}" if site_profile else "About Kehinde Omoyayi",
        description=site_profile.short_bio if site_profile else "Learn about Kehinde Omoyayi.",
        image=site_profile.profile_picture if site_profile else None,
        image_alt=site_profile.full_name if site_profile else "Kehinde Omoyayi",
    )

    context.update({
        "connect_links": Connect_Link.objects.all(),
        "certificates": Certificate.objects.all().order_by("-date_issued"),
        "about_stats": AboutStat.objects.all(),
        "about_pillars": AboutPillar.objects.all(),
        "signature_outcomes": SignatureOutcome.objects.all(),
    })

    return render(
        request,
        "portfolio/contact.html",
        context,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 404
# ──────────────────────────────────────────────────────────────────────────────

def custom_404(request, exception):
    site_profile = _get_site_profile()

    context = _base_context(
        request,
        site_profile,
        title="Page Not Found | Kehinde Omoyayi",
        description="The page you are looking for could not be found.",
        image=site_profile.profile_picture if site_profile else None,
    )

    context["previous"] = request.META.get("HTTP_REFERER")

    return render(
        request,
        "404.html",
        context,
        status=404,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Search API
# ──────────────────────────────────────────────────────────────────────────────

@require_GET
def search_view(request):
    q = request.GET.get("q", "").strip()
    scope = request.GET.get("scope", "all")

    if not q or len(q) < 2:
        return JsonResponse({
            "results": [],
            "q": q,
        })

    results = []

    if scope in ("all", "projects"):
        for p in Project.objects.filter(
            Q(name__icontains=q)
            | Q(summary__icontains=q)
            | Q(description__icontains=q),
            status="published",
        )[:5]:
            results.append({
                "type": "Project",
                "title": p.name,
                "url": p.get_absolute_url(),
                "meta": p.summary,
            })

    if scope in ("all", "dashboards"):
        for d in Dashboard.objects.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q),
            is_published=True,
        )[:5]:
            results.append({
                "type": "Dashboard",
                "title": d.title,
                "url": d.get_absolute_url(),
                "meta": d.description[:120] if d.description else "",
            })

    if scope in ("all", "research"):
        for pub in Publication.objects.filter(
            Q(title__icontains=q)
            | Q(abstract__icontains=q)
            | Q(authors__icontains=q),
            is_published=True,
        )[:5]:
            results.append({
                "type": "Research",
                "title": pub.title,
                "url": pub.get_absolute_url(),
                "meta": pub.abstract[:120] if pub.abstract else "",
            })

    if scope in ("all", "certificates"):
        for cert in Certificate.objects.filter(
            Q(title__icontains=q)
            | Q(issuing_organization__icontains=q),
            is_visible=True,
        )[:3]:
            results.append({
                "type": "Certificate",
                "title": cert.title,
                "url": "/certificates/",
                "meta": cert.issuing_organization,
            })

    if scope in ("all", "tools"):
        for tool in Tools.objects.filter(
            name__icontains=q,
            is_visible=True,
        )[:3]:
            results.append({
                "type": "Technology",
                "title": tool.name,
                "url": "/#expertise",
                "meta": "",
            })

    return JsonResponse({
        "results": results,
        "q": q,
    })
