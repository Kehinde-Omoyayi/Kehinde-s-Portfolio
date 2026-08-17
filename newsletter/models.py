import uuid
from django.db import models
from django.utils import timezone


class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    is_confirmed = models.BooleanField(
        default=True,
        help_text="If you turn on double opt-in later, unconfirmed subscribers won't receive campaigns."
    )
    is_active = models.BooleanField(default=True, help_text="Unticked automatically when someone unsubscribes.")
    unsubscribe_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-subscribed_at"]

    def __str__(self):
        return self.email


class Campaign(models.Model):
    subject = models.CharField(max_length=200)
    body_html = models.TextField(
        help_text="The email content. Basic HTML is fine, e.g. <p>, <a href=''>, <strong>."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    recipient_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        status = "sent" if self.sent_at else "draft"
        return f"{self.subject} ({status})"

    @property
    def is_sent(self):
        return self.sent_at is not None
