from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.sitemaps.views import sitemap

from main.sitemaps import (StaticViewSitemap,ProjectSitemap,DashboardSitemap,PublicationSitemap)

sitemaps = {
    "static": StaticViewSitemap,
    "projects": ProjectSitemap,
    "dashboards": DashboardSitemap,
    "publications": PublicationSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
    path('studio/', include('studio.urls', namespace='studio')),
    path('newsletter/', include('newsletter.urls')),
    path("sitemap.xml", sitemap,{"sitemaps": sitemaps},name="sitemap"),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

