import random

from django.conf import settings
from django.db import models
from django.utils import timezone


class PasswordResetOTP(models.Model):
    """A one-time 6-digit code emailed to a Studio user who's forgotten
    their password. Short-lived, single-use, and rate-limited against
    guessing via `attempts`."""

    OTP_LENGTH = 6
    TTL_MINUTES = 10
    MAX_ATTEMPTS = 5

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="password_reset_otps"
    )
    code = models.CharField(max_length=OTP_LENGTH)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"OTP for {self.user} ({'used' if self.is_used else 'active'})"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired and self.attempts < self.MAX_ATTEMPTS

    def verify(self, submitted_code):
        """Validate a submitted code. Increments the attempt counter on a
        miss so repeated guessing burns through MAX_ATTEMPTS."""
        if not self.is_valid:
            return False
        if submitted_code.strip() == self.code:
            self.is_used = True
            self.save(update_fields=["is_used"])
            return True
        self.attempts += 1
        self.save(update_fields=["attempts"])
        return False

    @classmethod
    def generate_for(cls, user):
        # Invalidate any previous outstanding codes so only the latest one works.
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        code = f"{random.randint(0, 10 ** cls.OTP_LENGTH - 1):0{cls.OTP_LENGTH}d}"
        return cls.objects.create(
            user=user,
            code=code,
            expires_at=timezone.now() + timezone.timedelta(minutes=cls.TTL_MINUTES),
        )
