from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
from django.utils import timezone

from .models import Subscriber


class CampaignSendResult:
    """Outcome of a campaign send — lets the caller show an accurate message
    instead of always claiming success even when delivery silently failed."""
    def __init__(self, sent, failed, total, email_configured):
        self.sent = sent
        self.failed = failed
        self.total = total
        self.email_configured = email_configured

    @property
    def all_failed(self):
        return self.total > 0 and self.sent == 0


def send_campaign(campaign, request=None):
    subscribers = Subscriber.objects.filter(is_active=True, is_confirmed=True)
    total = subscribers.count()
    sent = 0
    failed = 0

    if request is not None:
        base_url = request.build_absolute_uri("/")[:-1]
    else:
        base_url = getattr(settings, "SITE_BASE_URL", "http://127.0.0.1:8000")

    for subscriber in subscribers:
        unsubscribe_path = reverse("newsletter:unsubscribe", args=[subscriber.unsubscribe_token])
        unsubscribe_url = f"{base_url}{unsubscribe_path}"

        html_body = (
            f"{campaign.body_html}"
            f'<hr><p style="font-size:12px;color:#888;">'
            f'You are receiving this because you subscribed on the site. '
            f'<a href="{unsubscribe_url}">Unsubscribe</a></p>'
        )
        text_body = f"{campaign.subject}\n\n(View this email in HTML for full formatting.)\n\nUnsubscribe: {unsubscribe_url}"

        message = EmailMultiAlternatives(
            subject=campaign.subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[subscriber.email],
        )
        message.attach_alternative(html_body, "text/html")
        try:
            # fail_silently=False so a bad SMTP login, connection issue, etc.
            # is caught here and counted — not swallowed into a false
            # "sent successfully" result.
            message.send(fail_silently=False)
            sent += 1
        except Exception:
            failed += 1

    campaign.sent_at = timezone.now()
    campaign.recipient_count = sent
    campaign.save(update_fields=["sent_at", "recipient_count"])

    return CampaignSendResult(
        sent=sent,
        failed=failed,
        total=total,
        email_configured=getattr(settings, "EMAIL_IS_CONFIGURED", False),
    )
