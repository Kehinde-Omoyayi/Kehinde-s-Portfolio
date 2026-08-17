from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import (
    Category, Certificate, Connect_Link, Dashboard, Project, ProjectLink,
    Publication, Recommendation, Tools,
)


class PublicPageTests(TestCase):
    """Every public page should render successfully with real content."""

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Data Analytics")
        cls.project = Project.objects.create(
            name="Test Project", summary="A short summary",
            description="Full description", status="published",
        )
        cls.project.categories.add(cls.category)
        cls.dashboard = Dashboard.objects.create(title="Test Dashboard", is_published=True)
        cls.publication = Publication.objects.create(title="Test Publication", is_published=True)
        cls.certificate = Certificate.objects.create(title="Test Cert", issuing_organization="Test Org")

    def test_home_page(self):
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)

    def test_project_list(self):
        r = self.client.get(reverse("projects"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Test Project")

    def test_project_list_category_filter(self):
        r = self.client.get(reverse("projects"), {"category": self.category.slug})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Test Project")

    def test_project_detail(self):
        r = self.client.get(reverse("project_detail", args=[self.project.slug]))
        self.assertEqual(r.status_code, 200)

    def test_draft_project_is_not_public(self):
        draft = Project.objects.create(name="Draft Project", summary="s", description="d", status="draft")
        r = self.client.get(reverse("project_detail", args=[draft.slug]))
        self.assertEqual(r.status_code, 404)
        # And it shouldn't show up in the published list either.
        self.assertNotContains(self.client.get(reverse("projects")), "Draft Project")

    def test_dashboard_list_and_detail(self):
        self.assertEqual(self.client.get(reverse("dashboards")).status_code, 200)
        r = self.client.get(reverse("dashboard_detail", args=[self.dashboard.slug]))
        self.assertEqual(r.status_code, 200)

    def test_unpublished_dashboard_is_not_public(self):
        hidden = Dashboard.objects.create(title="Hidden Dashboard", is_published=False)
        r = self.client.get(reverse("dashboard_detail", args=[hidden.slug]))
        self.assertEqual(r.status_code, 404)

    def test_research_list_and_detail(self):
        self.assertEqual(self.client.get(reverse("research")).status_code, 200)
        r = self.client.get(reverse("research_detail", args=[self.publication.slug]))
        self.assertEqual(r.status_code, 200)

    def test_certificates_page_lists_visible_certs(self):
        r = self.client.get(reverse("certificate_list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Test Cert")

    def test_recommendations_page(self):
        Recommendation.objects.create(name="Jane Doe", message="Great work!")
        r = self.client.get(reverse("recommendation_list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Jane Doe")

    def test_activity_list_all_and_each_type(self):
        self.assertEqual(self.client.get(reverse("activity_list")).status_code, 200)
        for activity_type in ("project", "dashboard", "certificate", "research", "recommendation"):
            r = self.client.get(reverse("activity_list"), {"type": activity_type})
            self.assertEqual(r.status_code, 200, f"type={activity_type}")

    def test_activity_list_invalid_type_falls_back_to_all(self):
        r = self.client.get(reverse("activity_list"), {"type": "not-a-real-type"})
        self.assertEqual(r.status_code, 200)

    def test_contact_page(self):
        self.assertEqual(self.client.get(reverse("contact")).status_code, 200)

    def test_cv_view_page(self):
        self.assertEqual(self.client.get(reverse("cv_view")).status_code, 200)

    def test_home_page_renders_for_every_connect_link_platform(self):
        # Regression test: the homepage and footer used to fall back to
        # static image files (images/icons/<platform>.svg) that didn't
        # exist in the repo. Under WhiteNoise's manifest storage (used in
        # production) that raised a hard ValueError instead of a 404,
        # taking down every page site-wide the moment a Connect Link was
        # added for instagram/facebook/youtube/website.
        for platform, _ in Connect_Link.PLATFORM_CHOICES:
            Connect_Link.objects.create(platform=platform, url_or_handle="example.com", is_visible=True)
        r = self.client.get(reverse("home"))
        self.assertEqual(r.status_code, 200)

    def test_unknown_url_returns_custom_404(self):
        r = self.client.get("/this-page-does-not-exist/")
        self.assertEqual(r.status_code, 404)
        self.assertTemplateUsed(r, "404.html")


class SearchViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = Project.objects.create(
            name="Analytics Dashboard Project", summary="s", description="d", status="published",
        )
        cls.dashboard = Dashboard.objects.create(title="Sales Analytics Dashboard", is_published=True)
        cls.publication = Publication.objects.create(title="Analytics Research Paper", is_published=True)
        cls.certificate = Certificate.objects.create(title="Analytics Cert", issuing_organization="Org", is_visible=True)
        cls.tool = Tools.objects.create(name="Analytics Tool")

    def test_empty_query_returns_no_results(self):
        r = self.client.get(reverse("search"), {"q": ""})
        self.assertEqual(r.json()["results"], [])

    def test_single_char_query_returns_no_results(self):
        r = self.client.get(reverse("search"), {"q": "a"})
        self.assertEqual(r.json()["results"], [])

    def test_search_matches_all_types(self):
        r = self.client.get(reverse("search"), {"q": "Analytics"})
        types = {item["type"] for item in r.json()["results"]}
        self.assertEqual(types, {"Project", "Dashboard", "Research", "Certificate", "Technology"})

    def test_search_scope_limits_type(self):
        r = self.client.get(reverse("search"), {"q": "Analytics", "scope": "projects"})
        types = {item["type"] for item in r.json()["results"]}
        self.assertEqual(types, {"Project"})

    def test_search_results_link_to_working_urls(self):
        r = self.client.get(reverse("search"), {"q": "Analytics", "scope": "all"})
        for item in r.json()["results"]:
            if item["type"] in ("Project", "Dashboard", "Research"):
                self.assertEqual(self.client.get(item["url"]).status_code, 200, item)


class ModelBehaviorTests(TestCase):
    def test_project_link_capped_at_three(self):
        project = Project.objects.create(name="Link Project", summary="s", description="d")
        for i in range(3):
            ProjectLink.objects.create(project=project, url=f"https://example.com/{i}", link_type="github")
        fourth = ProjectLink(project=project, url="https://example.com/4", link_type="other")
        with self.assertRaises(ValidationError):
            fourth.full_clean()

    def test_project_is_currently_featured_reflects_is_featured(self):
        featured = Project.objects.create(name="Featured", summary="s", description="d", is_featured=True)
        not_featured = Project.objects.create(name="Not Featured", summary="s", description="d", is_featured=False)
        self.assertTrue(featured.is_currently_featured)
        self.assertFalse(not_featured.is_currently_featured)

    def test_connect_link_https_autoprepend_for_web_platforms(self):
        link = Connect_Link.objects.create(platform="github", url_or_handle="github.com/test")
        self.assertEqual(link.url_or_handle, "https://github.com/test")

    def test_connect_link_email_survives_form_submission_unmangled(self):
        # Regression test: url_or_handle used to be a URLField, which
        # silently rewrote a bare email like "me@example.com" into
        # "http://me@example.com" the moment it passed through a
        # ModelForm (i.e. every time it's saved via Studio) — breaking
        # the mailto: link this field feeds into `href`.
        from django.forms import modelform_factory
        Form = modelform_factory(Connect_Link, fields=["platform", "url_or_handle", "is_visible"])
        form = Form(data={"platform": "email", "url_or_handle": "me@example.com", "is_visible": True})
        self.assertTrue(form.is_valid(), form.errors)
        obj = form.save()
        self.assertEqual(obj.url_or_handle, "me@example.com")
        self.assertEqual(obj.href, "mailto:me@example.com")

    def test_connect_link_whatsapp_href(self):
        link = Connect_Link.objects.create(platform="whatsapp", url_or_handle="15551234567")
        self.assertEqual(link.href, "https://wa.me/15551234567")

    def test_project_without_cover_image_renders_fine(self):
        # Regression test: cover_image used to be "required" with a
        # default pointing at a file that didn't exist anywhere in the
        # repo (and wasn't shippable via git, since /media/ is
        # gitignored). Creating a project through Studio without
        # uploading a cover produced a permanently broken image on the
        # live site. It's genuinely optional now.
        project = Project.objects.create(
            name="No Cover Project", summary="s", description="d", status="published",
        )
        self.assertFalse(project.cover_image)
        r = self.client.get(reverse("project_detail", args=[project.slug]))
        self.assertEqual(r.status_code, 200)
        r = self.client.get(reverse("projects"))
        self.assertEqual(r.status_code, 200)

    def test_certificate_has_no_broken_get_absolute_url(self):
        # Certificate has no slug/detail page; get_absolute_url used to
        # reference a nonexistent `slug` field and would raise if ever
        # called. It should simply not exist.
        cert = Certificate.objects.create(title="X", issuing_organization="Y")
        self.assertFalse(hasattr(cert, "get_absolute_url"))
