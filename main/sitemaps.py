from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Project, Dashboard, Publication


class StaticViewSitemap(Sitemap):
    protocol = "https"
    changefreq = "weekly"
    priority = 1.0

    def items(self):
        return [
            "home",
            "projects",
            "dashboards",
            "research",
            "certificate_list",
            "recommendation_list",
            "activity_list",
            "cv_view",
            "contact",
        ]

    def location(self, item):
        return reverse(item)


class ProjectSitemap(Sitemap):
    protocol = "https"
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return Project.objects.filter(
            status="published"
        )

    def lastmod(self, obj):
        return obj.updated_at


class DashboardSitemap(Sitemap):
    protocol = "https"
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return Dashboard.objects.filter(
            is_published=True
        )

    def lastmod(self, obj):
        return obj.updated_at


class PublicationSitemap(Sitemap):
    protocol = "https"
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return Publication.objects.filter(
            is_published=True
        )

    def lastmod(self, obj):
        return obj.published_at