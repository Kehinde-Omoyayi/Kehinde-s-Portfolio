from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from .models import Campaign, Subscriber
from .utils import send_campaign


class SubscribeTests(TestCase):
    def setUp(self):
        cache.clear()  # subscribe view is rate-limited by IP via the cache

    def test_new_subscription_creates_active_subscriber(self):
        self.client.post(reverse("newsletter:subscribe"), {"email": "new@example.com"}, follow=True)
        self.assertTrue(Subscriber.objects.filter(email="new@example.com", is_active=True).exists())

    def test_duplicate_active_subscription_does_not_duplicate_row(self):
        Subscriber.objects.create(email="dup@example.com")
        self.client.post(reverse("newsletter:subscribe"), {"email": "dup@example.com"}, follow=True)
        self.assertEqual(Subscriber.objects.filter(email="dup@example.com").count(), 1)

    def test_reactivates_inactive_subscriber(self):
        sub = Subscriber.objects.create(email="gone@example.com", is_active=False)
        self.client.post(reverse("newsletter:subscribe"), {"email": "gone@example.com"}, follow=True)
        sub.refresh_from_db()
        self.assertTrue(sub.is_active)
        self.assertIsNone(sub.unsubscribed_at)

    def test_invalid_email_is_rejected(self):
        self.client.post(reverse("newsletter:subscribe"), {"email": "not-an-email"}, follow=True)
        self.assertFalse(Subscriber.objects.filter(email="not-an-email").exists())

    def test_email_matching_is_case_insensitive(self):
        Subscriber.objects.create(email="case@example.com")
        self.client.post(reverse("newsletter:subscribe"), {"email": "CASE@EXAMPLE.COM"}, follow=True)
        self.assertEqual(Subscriber.objects.filter(email__iexact="case@example.com").count(), 1)

    def test_rate_limit_blocks_after_five_per_minute(self):
        for i in range(5):
            self.client.post(reverse("newsletter:subscribe"), {"email": f"rl{i}@example.com"})
        self.client.post(reverse("newsletter:subscribe"), {"email": "rl-sixth@example.com"})
        self.assertFalse(Subscriber.objects.filter(email="rl-sixth@example.com").exists())

    def test_redirect_target_ignores_foreign_referer(self):
        r = self.client.post(
            reverse("newsletter:subscribe"), {"email": "safe@example.com"},
            HTTP_REFERER="https://evil-external-site.example/",
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.url.startswith("/"))
        self.assertNotIn("evil-external-site", r.url)


class UnsubscribeTests(TestCase):
    def test_valid_token_unsubscribes(self):
        sub = Subscriber.objects.create(email="byebye@example.com")
        r = self.client.get(reverse("newsletter:unsubscribe", args=[sub.unsubscribe_token]))
        self.assertEqual(r.status_code, 200)
        sub.refresh_from_db()
        self.assertFalse(sub.is_active)
        self.assertIsNotNone(sub.unsubscribed_at)

    def test_invalid_token_404s(self):
        r = self.client.get(reverse("newsletter:unsubscribe", args=["00000000-0000-0000-0000-000000000000"]))
        self.assertEqual(r.status_code, 404)


class SendCampaignTests(TestCase):
    def test_sends_only_to_active_confirmed_subscribers(self):
        Subscriber.objects.create(email="active@example.com", is_active=True, is_confirmed=True)
        Subscriber.objects.create(email="inactive@example.com", is_active=False, is_confirmed=True)
        Subscriber.objects.create(email="unconfirmed@example.com", is_active=True, is_confirmed=False)
        campaign = Campaign.objects.create(subject="Hi", body_html="<p>Hello</p>")

        result = send_campaign(campaign)

        self.assertEqual(result.sent, 1)
        self.assertEqual(result.failed, 0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["active@example.com"])
        campaign.refresh_from_db()
        self.assertIsNotNone(campaign.sent_at)
        self.assertEqual(campaign.recipient_count, 1)

    def test_unsubscribe_link_present_in_body(self):
        sub = Subscriber.objects.create(email="link@example.com")
        campaign = Campaign.objects.create(subject="Hi", body_html="<p>Hello</p>")
        send_campaign(campaign)
        self.assertIn(str(sub.unsubscribe_token), mail.outbox[0].alternatives[0][0])
