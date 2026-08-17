from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_page, name='home'),
    path("projects/", views.project_list, name="projects"),
    path("projects/<slug:slug>/", views.project_detail, name="project_detail"),
    path("dashboards/", views.dashboard_list, name="dashboards"),
    path("dashboards/<slug:slug>/", views.dashboard_detail, name="dashboard_detail"),
    path("cv/", views.cv_downloads, name="cv_downloads"),
    path("cv_view/", views.cv_downloads, name="cv_view"),
    # Tracked download endpoints
    path("cv/download/", views.cv_download_tracked, name="cv_download"),
    path("cv/track/", views.cv_track_ping, name="cv_track"),
    path("projects/<int:pk>/download/", views.project_pdf_download, name="project_pdf_download"),
    path("projects/<int:pk>/track/", views.project_pdf_track_ping, name="project_pdf_track"),
    path("certificates/", views.certificate_list, name="certificate_list"),
    path("recommendations/", views.recommendation_list, name="recommendation_list"),
    path("activity/", views.activity_list, name="activity_list"),
    path("research/", views.research_list, name="research"),
    path("research/<slug:slug>/", views.research_detail, name="research_detail"),
    path("contact/", views.contact, name="contact"),
    # Search API
    path("search/", views.search_view, name="search"),
]