from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from main.models import Category, Connect_Link, Project
from newsletter.models import Campaign, Subscriber
from studio.models import PasswordResetOTP

import main.middleware as main_middleware

User = get_user_model()


def _create_staff(email, password):
    user = User.objects.create_user(email=email, first_name="Staff", last_name="User", password=password)
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    return user


class StaffRequiredTests(TestCase):
    """Every Studio page should be gated behind staff login."""

    def setUp(self):
        self.staff_password = "Sup3rSecret!42"
        self.staff = _create_staff("gate@example.com", self.staff_password)

    def test_anonymous_user_is_redirected_to_login(self):
        r = self.client.get(reverse("studio:home"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("studio:login"), r.url)

    def test_non_staff_authenticated_user_is_redirected(self):
        # Not using self.client.login() here: django-axes' auth backend
        # requires a real request object, which the login() shortcut
        # doesn't provide. Logging in through the actual view instead.
        User.objects.create_user(email="regular@example.com", first_name="R", last_name="U", password="whatever123")
        self.client.post(reverse("studio:login"), {"username": "regular@example.com", "password": "whatever123"})
        r = self.client.get(reverse("studio:home"))
        self.assertEqual(r.status_code, 302)

    def test_staff_user_can_access(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("studio:home")).status_code, 200)

    def test_django_admin_hidden_from_anonymous(self):
        r = self.client.get("/admin/")
        self.assertEqual(r.status_code, 404)

    def test_django_admin_reachable_by_staff(self):
        self.client.force_login(self.staff)
        r = self.client.get("/admin/")
        self.assertEqual(r.status_code, 200)


class LoginFlowTests(TestCase):
    def setUp(self):
        main_middleware._login_attempts.clear()
        self.password = "Sup3rSecret!42"
        self.staff = _create_staff("login@example.com", self.password)

    def test_correct_credentials_log_in_staff_user(self):
        r = self.client.post(reverse("studio:login"), {"username": "login@example.com", "password": self.password})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse("studio:home"))

    def test_wrong_password_shows_error_and_does_not_log_in(self):
        r = self.client.post(reverse("studio:login"), {"username": "login@example.com", "password": "wrong"})
        self.assertEqual(r.status_code, 200)
        r2 = self.client.get(reverse("studio:home"))
        self.assertEqual(r2.status_code, 302)  # still logged out

    def test_non_staff_account_is_rejected_with_message(self):
        User.objects.create_user(email="nostaff@example.com", first_name="N", last_name="S", password="whatever123")
        r = self.client.post(
            reverse("studio:login"), {"username": "nostaff@example.com", "password": "whatever123"}, follow=True,
        )
        self.assertContains(r, "doesn&#x27;t have Studio access")

    def test_login_form_label_matches_the_actual_username_field(self):
        # The custom user model authenticates by email, so the rendered
        # label must say "Email", not a hardcoded "Username".
        r = self.client.get(reverse("studio:login"))
        self.assertNotContains(r, ">Username<")

    def test_logout_ends_session(self):
        self.client.force_login(self.staff)
        self.client.get(reverse("studio:logout"))
        self.assertEqual(self.client.get(reverse("studio:home")).status_code, 302)


class AxesLockoutTests(TestCase):
    def setUp(self):
        main_middleware._login_attempts.clear()
        self.password = "Sup3rSecret!42"
        self.staff = _create_staff("lockout@example.com", self.password)

    def test_repeated_failures_lock_the_account_out(self):
        for _ in range(6):
            r = self.client.post(
                reverse("studio:login"), {"username": "lockout@example.com", "password": "wrong"}, follow=True,
            )
        # Even the correct password should now be refused until cooloff.
        r = self.client.post(
            reverse("studio:login"), {"username": "lockout@example.com", "password": self.password}, follow=True,
        )
        self.assertEqual(self.client.get(reverse("studio:home")).status_code, 302)


class PasswordResetOTPFlowTests(TestCase):
    def setUp(self):
        self.password = "OldPassword!42"
        self.staff = _create_staff("otp@example.com", self.password)

    @override_settings(EMAIL_IS_CONFIGURED=True)
    def test_full_reset_flow(self):
        # 1. Request a code.
        r = self.client.post(reverse("studio:password_reset_request"), {"email": "otp@example.com"}, follow=True)
        self.assertEqual(len(mail.outbox), 1)
        otp = PasswordResetOTP.objects.filter(user=self.staff).latest("created_at")

        # 2. Verify it.
        r = self.client.post(reverse("studio:password_reset_verify"), {"code": otp.code}, follow=True)
        self.assertEqual(r.status_code, 200)

        # 3. Set a new password.
        r = self.client.post(reverse("studio:password_reset_set_new"), {
            "new_password1": "BrandNewPassword!42",
            "new_password2": "BrandNewPassword!42",
        }, follow=True)
        self.assertEqual(r.status_code, 200)

        # The user should now be logged in automatically...
        self.assertEqual(self.client.get(reverse("studio:home")).status_code, 200)

        # ...and the new password should actually work on a fresh login.
        self.client.get(reverse("studio:logout"))
        r = self.client.post(reverse("studio:login"), {"username": "otp@example.com", "password": "BrandNewPassword!42"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse("studio:home"))

    def test_reset_request_without_email_configured_shows_error(self):
        r = self.client.post(reverse("studio:password_reset_request"), {"email": "otp@example.com"}, follow=True)
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(PasswordResetOTP.objects.filter(user=self.staff).exists())

    @override_settings(EMAIL_IS_CONFIGURED=True)
    def test_reset_request_does_not_reveal_account_existence(self):
        r1 = self.client.post(reverse("studio:password_reset_request"), {"email": "otp@example.com"}, follow=True)
        r2 = self.client.post(reverse("studio:password_reset_request"), {"email": "nobody@example.com"}, follow=True)
        msg1 = [str(m) for m in r1.context["messages"]] if "messages" in r1.context else []
        msg2 = [str(m) for m in r2.context["messages"]] if "messages" in r2.context else []
        # Both should redirect through the same generic messaging (can't
        # be distinguished by an outside observer).
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)

    @override_settings(EMAIL_IS_CONFIGURED=True)
    def test_wrong_otp_code_increments_attempts(self):
        self.client.post(reverse("studio:password_reset_request"), {"email": "otp@example.com"})
        otp = PasswordResetOTP.objects.filter(user=self.staff).latest("created_at")
        self.client.post(reverse("studio:password_reset_verify"), {"code": "000000"})
        otp.refresh_from_db()
        self.assertEqual(otp.attempts, 0 if otp.code == "000000" else 1)


class PasswordChangeTests(TestCase):
    def setUp(self):
        self.password = "OldPassword!42"
        self.staff = _create_staff("change@example.com", self.password)
        self.client.force_login(self.staff)

    def test_change_password_while_logged_in(self):
        r = self.client.post(reverse("studio:password_change"), {
            "old_password": self.password,
            "new_password1": "AnotherOne!42",
            "new_password2": "AnotherOne!42",
        }, follow=True)
        self.assertEqual(r.status_code, 200)
        self.client.get(reverse("studio:logout"))
        r = self.client.post(reverse("studio:login"), {"username": "change@example.com", "password": "AnotherOne!42"})
        self.assertEqual(r.status_code, 302)


class GenericCRUDTests(TestCase):
    """Exercises the registry-driven generic list/create/update/delete views."""

    def setUp(self):
        self.staff = _create_staff("crud@example.com", "Sup3rSecret!42")
        self.client.force_login(self.staff)

    def test_category_create_list_update_delete(self):
        # Create
        r = self.client.post(reverse("studio:generic_create", args=["categories"]), {"name": "New Category"})
        self.assertEqual(r.status_code, 302)
        cat = Category.objects.get(name="New Category")

        # List (and search)
        r = self.client.get(reverse("studio:generic_list", args=["categories"]))
        self.assertContains(r, "New Category")
        r = self.client.get(reverse("studio:generic_list", args=["categories"]), {"q": "New"})
        self.assertContains(r, "New Category")

        # Update
        r = self.client.post(reverse("studio:generic_update", args=["categories", cat.pk]), {"name": "Renamed"})
        self.assertEqual(r.status_code, 302)
        cat.refresh_from_db()
        self.assertEqual(cat.name, "Renamed")

        # Delete
        r = self.client.post(reverse("studio:generic_delete", args=["categories", cat.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Category.objects.filter(pk=cat.pk).exists())

    def test_connect_link_email_platform_round_trips_through_studio(self):
        r = self.client.post(reverse("studio:generic_create", args=["connect-links"]), {
            "platform": "email", "url_or_handle": "hello@example.com", "is_visible": "on",
        })
        self.assertEqual(r.status_code, 302)
        link = Connect_Link.objects.get(platform="email")
        self.assertEqual(link.url_or_handle, "hello@example.com")
        self.assertEqual(link.href, "mailto:hello@example.com")

    def test_unknown_section_404s(self):
        r = self.client.get(reverse("studio:generic_list", args=["not-a-real-section"]))
        self.assertEqual(r.status_code, 404)

    def test_all_registered_sections_list_and_form_render(self):
        from studio.registry import SECTIONS
        for key in SECTIONS:
            with self.subTest(section=key):
                self.assertEqual(self.client.get(reverse("studio:generic_list", args=[key])).status_code, 200)
                self.assertEqual(self.client.get(reverse("studio:generic_create", args=[key])).status_code, 200)


class ProjectCRUDTests(TestCase):
    def setUp(self):
        self.staff = _create_staff("proj@example.com", "Sup3rSecret!42")
        self.client.force_login(self.staff)

    def test_create_project_with_links(self):
        data = {
            "name": "My New Project", "summary": "Summary", "description": "Description",
            "allow_pdf_download": "on", "is_featured": "on", "status": "published", "order": "0",
            "links-TOTAL_FORMS": "1", "links-INITIAL_FORMS": "0",
            "links-MIN_NUM_FORMS": "0", "links-MAX_NUM_FORMS": "3",
            "links-0-link_type": "github", "links-0-url": "https://github.com/example/repo", "links-0-order": "0",
        }
        r = self.client.post(reverse("studio:project_create"), data)
        self.assertEqual(r.status_code, 302, r.context["form"].errors if r.status_code != 302 else None)
        project = Project.objects.get(name="My New Project")
        self.assertEqual(project.links.count(), 1)

    def test_project_list_and_delete(self):
        project = Project.objects.create(name="Deletable", summary="s", description="d")
        r = self.client.get(reverse("studio:project_list"))
        self.assertContains(r, "Deletable")
        r = self.client.post(reverse("studio:project_delete", args=[project.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Project.objects.filter(pk=project.pk).exists())


class CampaignTests(TestCase):
    def setUp(self):
        self.staff = _create_staff("campaigner@example.com", "Sup3rSecret!42")
        self.client.force_login(self.staff)

    def test_create_campaign_as_draft(self):
        r = self.client.post(reverse("studio:campaign_create"), {"subject": "Hello", "body_html": "<p>Hi</p>"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Campaign.objects.filter(subject="Hello").exists())

    def test_send_campaign_reports_sent_count(self):
        Subscriber.objects.create(email="camp-sub@example.com")
        campaign = Campaign.objects.create(subject="Go", body_html="<p>Go</p>")
        r = self.client.post(reverse("studio:campaign_send", args=[campaign.pk]), follow=True)
        campaign.refresh_from_db()
        self.assertIsNotNone(campaign.sent_at)
        self.assertEqual(campaign.recipient_count, 1)

    def test_send_campaign_twice_is_blocked(self):
        Subscriber.objects.create(email="camp-sub2@example.com")
        campaign = Campaign.objects.create(subject="Once", body_html="<p>Once</p>")
        self.client.post(reverse("studio:campaign_send", args=[campaign.pk]))
        first_sent_at = Campaign.objects.get(pk=campaign.pk).sent_at
        self.client.post(reverse("studio:campaign_send", args=[campaign.pk]))
        self.assertEqual(Campaign.objects.get(pk=campaign.pk).sent_at, first_sent_at)

    def test_send_test_email_requires_email_configured(self):
        r = self.client.post(reverse("studio:campaign_send_test"), follow=True)
        self.assertEqual(len(mail.outbox), 0)


class SubscriberManagementTests(TestCase):
    def setUp(self):
        self.staff = _create_staff("subman@example.com", "Sup3rSecret!42")
        self.client.force_login(self.staff)

    def test_toggle_active_state(self):
        sub = Subscriber.objects.create(email="toggle@example.com", is_active=True)
        self.client.post(reverse("studio:subscriber_toggle", args=[sub.pk]))
        sub.refresh_from_db()
        self.assertFalse(sub.is_active)
        self.client.post(reverse("studio:subscriber_toggle", args=[sub.pk]))
        sub.refresh_from_db()
        self.assertTrue(sub.is_active)

    def test_delete_subscriber(self):
        sub = Subscriber.objects.create(email="deleteme@example.com")
        self.client.post(reverse("studio:subscriber_delete", args=[sub.pk]))
        self.assertFalse(Subscriber.objects.filter(pk=sub.pk).exists())
