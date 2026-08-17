from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Q, Count
from django.views.decorators.http import require_GET
from .activity import get_activity_feed, ACTIVITY_TYPES
from .models import (
    Project, Dashboard, DashboardMetric, Certificate, Recommendation, Tools,
    Publication, CVDocument, Category, SiteProfile,
    Connect_Link, Currently_Focused, Open_Roles, SignatureOutcome, AboutPillar, AboutStat,
    DownloadLog, PageView,
)


# ── Helpers ────────────────────────────────────────────────────────────────────
def _get_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _log_pageview(request):
    try:
        PageView.objects.create(path=request.path, ip_address=_get_ip(request))
    except Exception:
        pass


# ── Public views ───────────────────────────────────────────────────────────────
def home_page(request):
    _log_pageview(request)
    site_profile = SiteProfile.objects.select_related(
        'active_cv').prefetch_related('highlights', 'role_titles').first()
    latest_activity = get_activity_feed()[:6]

    context = {
        "site_profile":       site_profile,
        "open_roles":         Open_Roles.objects.all(),
        "currently_focused":  Currently_Focused.objects.all(),
        "social_links":       Connect_Link.objects.filter(is_visible=True),
        "stat_projects":      Project.objects.filter(status="published").count(),
        "stat_dashboards":    Dashboard.objects.filter(is_published=True).count(),
        "stat_research":      Publication.objects.filter(is_published=True).count(),
        "stat_technologies":  Tools.objects.filter(is_visible=True).count(),
        "stat_certificates":  Certificate.objects.filter(is_visible=True).count(),
        "featured_projects":  Project.objects.filter(status="published", is_featured=True)
                              .prefetch_related('categories', 'technologies', 'links')
                              .order_by('order', '-created_at')[:6],
        "featured_dashboards": Dashboard.objects.filter(is_published=True, is_featured=True)
                               .prefetch_related('metrics', 'categories', 'technologies')
                               .order_by('order', '-created_at')[:3],
        "featured_research":   Publication.objects.filter(is_published=True)
                               .prefetch_related('categories')
                               .order_by('-published_at')[:3],
        "latest_activity": latest_activity,
        "tools":               Tools.objects.filter(is_visible=True),
        "recommendations":     Recommendation.objects.filter(is_visible=True)[:6],
        "motion_items": [
            {"image_url": p.cover_image.url, "caption": p.name}
            for p in Project.objects.filter(is_featured=True).exclude(cover_image="")
        ],
    }
    return render(request, 'home/index.html', context)


def project_list(request):
    _log_pageview(request)
    projects = Project.objects.filter(status="published")
    category_slug = request.GET.get("category")
    if category_slug:
        projects = projects.filter(categories__slug=category_slug)
    paginator = Paginator(projects, 9)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "portfolio/project_list.html", {
        "page_obj": page_obj,
        "categories": Category.objects.filter(projects__isnull=False).distinct(),
        "selected_category": category_slug,
        "social_links": Connect_Link.objects.filter(is_visible=True),
    })


def project_detail(request, slug):
    _log_pageview(request)
    project = get_object_or_404(Project, slug=slug, status="published")
    return render(request, "portfolio/project_detail.html", {
        "project": project,
        "social_links": Connect_Link.objects.filter(is_visible=True),
    })


def dashboard_list(request):
    _log_pageview(request)
    dashboards = Dashboard.objects.filter(is_published=True)
    return render(request, "portfolio/dashboard_list.html", {
        "dashboards": dashboards,
        "social_links": Connect_Link.objects.filter(is_visible=True),
    })


def dashboard_detail(request, slug):
    _log_pageview(request)
    dashboard = get_object_or_404(Dashboard, slug=slug, is_published=True)
    return render(request, "portfolio/dashboard_detail.html", {
        "dashboard": dashboard,
        "social_links": Connect_Link.objects.filter(is_visible=True),
    })


def cv_downloads(request):
    _log_pageview(request)
    site_profile = SiteProfile.objects.first()
    profile_cv = site_profile.active_cv if site_profile else None
    return render(request, "portfolio/cv.html", {
        "profile_cv": profile_cv,
        "site_profile": site_profile,
        "social_links": Connect_Link.objects.filter(is_visible=True),
    })


def cv_download_tracked(request):
    """Log the CV download and redirect to the file (for backward compat)."""
    site_profile = SiteProfile.objects.select_related('active_cv').first()
    if not site_profile or not site_profile.active_cv:
        from django.http import Http404
        raise Http404("No CV available")
    cv = site_profile.active_cv
    try:
        DownloadLog.objects.create(
            file_type='cv',
            object_id=cv.pk,
            object_title=cv.title,
            ip_address=_get_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:400],
        )
    except Exception:
        pass
    # If called via fetch (tracking ping), return JSON
    if request.headers.get('Accept', '').startswith('application/json') or request.GET.get('track') == '1':
        return JsonResponse({'ok': True})
    return redirect(cv.file.url)


def cv_track_ping(request):
    """Lightweight GET endpoint to log CV download without redirect."""
    site_profile = SiteProfile.objects.select_related('active_cv').first()
    if site_profile and site_profile.active_cv:
        cv = site_profile.active_cv
        try:
            DownloadLog.objects.create(
                file_type='cv',
                object_id=cv.pk,
                object_title=cv.title,
                ip_address=_get_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:400],
            )
        except Exception:
            pass
    return JsonResponse({'ok': True})


def project_pdf_download(request, pk):
    """Log the project PDF download and redirect (or return JSON for fetch tracking)."""
    project = get_object_or_404(Project, pk=pk, status="published")
    if not project.pdf_report:
        from django.http import Http404
        raise Http404("No PDF for this project")
    try:
        DownloadLog.objects.create(
            file_type='project_pdf',
            object_id=project.pk,
            object_title=project.name,
            ip_address=_get_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:400],
        )
    except Exception:
        pass
    if request.headers.get('Accept', '').startswith('application/json') or request.GET.get('track') == '1':
        return JsonResponse({'ok': True})
    return redirect(project.pdf_report.url)


def project_pdf_track_ping(request, pk):
    """Lightweight GET endpoint to log project PDF download without redirect."""
    project = get_object_or_404(Project, pk=pk, status="published")
    if project.pdf_report:
        try:
            DownloadLog.objects.create(
                file_type='project_pdf',
                object_id=project.pk,
                object_title=project.name,
                ip_address=_get_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:400],
            )
        except Exception:
            pass
    return JsonResponse({'ok': True})


def certificate_list(request):
    _log_pageview(request)
    certificates = Certificate.objects.filter(is_visible=True)
    return render(request, "portfolio/certificates.html", {
        "certificates": certificates,
        "social_links": Connect_Link.objects.filter(is_visible=True),
    })


def recommendation_list(request):
    _log_pageview(request)
    recommendations = Recommendation.objects.filter(is_visible=True)
    return render(request, "portfolio/recommendations.html", {
        "recommendations": recommendations,
        "social_links": Connect_Link.objects.filter(is_visible=True),
    })


def activity_list(request):
    _log_pageview(request)
    activity_type = request.GET.get("type")
    valid_types = dict(ACTIVITY_TYPES)
    if activity_type not in valid_types:
        activity_type = None
    entries = get_activity_feed(activity_type)
    paginator = Paginator(entries, 8)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "portfolio/activity_list.html", {
        "page_obj": page_obj,
        "activity_types": ACTIVITY_TYPES,
        "selected_type": activity_type,
        "social_links": Connect_Link.objects.filter(is_visible=True),
    })


def research_list(request):
    _log_pageview(request)
    publication = Publication.objects.filter(is_published=True)
    category_slug = request.GET.get("category")
    if category_slug:
        publication = publication.filter(categories__slug=category_slug)
    paginator = Paginator(publication, 9)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "portfolio/research_list.html", {
        "page_obj": page_obj,
        "categories": Category.objects.filter(publications__isnull=False).distinct(),
        "selected_category": category_slug,
        "social_links": Connect_Link.objects.filter(is_visible=True),
    })


def research_detail(request, slug):
    _log_pageview(request)
    publication = get_object_or_404(Publication, slug=slug, is_published=True)
    return render(request, "portfolio/research_detail.html", {
        "publication": publication,
        "social_links": Connect_Link.objects.filter(is_visible=True),
    })


def contact(request):
    _log_pageview(request)
    site_profile  = SiteProfile.objects.first()
    connect_links = Connect_Link.objects.all()
    certificates  = Certificate.objects.all().order_by("-date_issued")
    return render(request, "portfolio/contact.html", {
        "site_profile":       site_profile,
        "connect_links":      connect_links,
        "social_links":       Connect_Link.objects.filter(is_visible=True),
        "certificates":       certificates,
        "about_stats":        AboutStat.objects.all(),
        "about_pillars":      AboutPillar.objects.all(),
        "signature_outcomes": SignatureOutcome.objects.all(),
    })


def custom_404(request, exception):
    previous = request.META.get("HTTP_REFERER")
    return render(request, "404.html", {"previous": previous}, status=404)


# ── Search API ─────────────────────────────────────────────────────────────────
@require_GET
def search_view(request):
    q = request.GET.get("q", "").strip()
    scope = request.GET.get("scope", "all")   # 'all', 'projects', 'research', etc.

    if not q or len(q) < 2:
        return JsonResponse({"results": [], "q": q})

    results = []

    if scope in ("all", "projects"):
        for p in Project.objects.filter(
            Q(name__icontains=q) | Q(summary__icontains=q) | Q(description__icontains=q),
            status="published"
        )[:5]:
            results.append({
                "type": "Project",
                "title": p.name,
                "url": p.get_absolute_url(),
                "meta": p.summary,
            })

    if scope in ("all", "dashboards"):
        for d in Dashboard.objects.filter(
            Q(title__icontains=q) | Q(description__icontains=q),
            is_published=True
        )[:5]:
            results.append({
                "type": "Dashboard",
                "title": d.title,
                "url": d.get_absolute_url(),
                "meta": d.description[:120] if d.description else "",
            })

    if scope in ("all", "research"):
        for pub in Publication.objects.filter(
            Q(title__icontains=q) | Q(abstract__icontains=q) | Q(authors__icontains=q),
            is_published=True
        )[:5]:
            results.append({
                "type": "Research",
                "title": pub.title,
                "url": pub.get_absolute_url(),
                "meta": pub.abstract[:120] if pub.abstract else "",
            })

    if scope in ("all", "certificates"):
        for cert in Certificate.objects.filter(
            Q(title__icontains=q) | Q(issuing_organization__icontains=q),
            is_visible=True
        )[:3]:
            results.append({
                "type": "Certificate",
                "title": cert.title,
                "url": "/certificates/",
                "meta": cert.issuing_organization,
            })

    if scope in ("all", "tools"):
        for tool in Tools.objects.filter(
            Q(name__icontains=q),
            is_visible=True
        )[:3]:
            results.append({
                "type": "Technology",
                "title": tool.name,
                "url": "/#expertise",
                "meta": "",
            })

    return JsonResponse({"results": results, "q": q})