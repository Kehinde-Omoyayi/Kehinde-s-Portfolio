from django.urls import path
from . import views

app_name = "studio"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("password-reset/", views.password_reset_request, name="password_reset_request"),
    path("password-reset/verify/", views.password_reset_verify, name="password_reset_verify"),
    path("password-reset/new/", views.password_reset_set_new, name="password_reset_set_new"),
    path("password-change/", views.password_change, name="password_change"),
    path("", views.home, name="home"),
    path("analytics/reset/", views.reset_analytics, name="reset_analytics"),
    path("profile/", views.profile_edit, name="profile_edit"),
    path("projects/", views.project_list, name="project_list"),
    path("projects/add/", views.project_create, name="project_create"),
    path("projects/<int:pk>/edit/", views.project_update, name="project_update"),
    path("projects/<int:pk>/delete/", views.project_delete, name="project_delete"),
    path("dashboards/", views.dashboard_list, name="dashboard_list"),
    path("dashboards/add/", views.dashboard_create, name="dashboard_create"),
    path("dashboards/<int:pk>/edit/", views.dashboard_update, name="dashboard_update"),
    path("dashboards/<int:pk>/delete/", views.dashboard_delete, name="dashboard_delete"),
    path("campaigns/", views.campaign_list, name="campaign_list"),
    path("campaigns/add/", views.campaign_create, name="campaign_create"),
    path("campaigns/send-test/", views.campaign_send_test, name="campaign_send_test"),
    path("campaigns/<int:pk>/send/", views.campaign_send, name="campaign_send"),
    path("subscribers/", views.subscriber_list, name="subscriber_list"),
    path("subscribers/<int:pk>/toggle/", views.subscriber_toggle, name="subscriber_toggle"),
    path("subscribers/<int:pk>/delete/", views.subscriber_delete, name="subscriber_delete"),
    path("<slug:section_key>/", views.generic_list, name="generic_list"),
    path("<slug:section_key>/add/", views.generic_create, name="generic_create"),
    path("<slug:section_key>/<int:pk>/edit/", views.generic_update, name="generic_update"),
    path("<slug:section_key>/<int:pk>/delete/", views.generic_delete, name="generic_delete"),
]
