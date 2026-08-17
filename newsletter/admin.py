from django.contrib import admin, messages

from .models import Subscriber, Campaign
from .utils import send_campaign


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "is_active", "is_confirmed", "subscribed_at")
    list_filter = ("is_active", "is_confirmed")
    search_fields = ("email",)


@admin.action(description="Send selected campaign(s) to every active subscriber now")
def send_selected_campaigns(modeladmin, request, queryset):
    for campaign in queryset:
        if campaign.is_sent:
            messages.warning(request, f'"{campaign.subject}" was already sent on {campaign.sent_at:%Y-%m-%d} — skipped.')
            continue
        result = send_campaign(campaign, request=request)
        if not result.email_configured:
            messages.warning(
                request,
                f'"{campaign.subject}" marked as sent to {result.sent} subscriber(s), but email '
                "isn't configured yet — nothing actually left the server."
            )
        elif result.failed:
            messages.warning(
                request,
                f'"{campaign.subject}" sent to {result.sent} of {result.total} subscriber(s) — '
                f'{result.failed} failed to deliver.'
            )
        else:
            messages.success(request, f'Sent "{campaign.subject}" to {result.sent} subscriber(s).')


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("subject", "is_sent", "recipient_count", "created_at", "sent_at")
    readonly_fields = ("sent_at", "recipient_count")
    actions = [send_selected_campaigns]
    fieldsets = (
        (None, {"fields": ("subject", "body_html")}),
        ("Send status (read only)", {"fields": ("sent_at", "recipient_count")}),
    )
