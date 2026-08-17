from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import SubscribeForm
from .models import Subscriber
from django_ratelimit.decorators import ratelimit


def _safe_redirect_target(request):
    """Redirect back to wherever the subscribe form was submitted from.
    Falls back to the home page (never to a bare, unregistered namespace)
    and only honours the referer if it actually points at this site."""
    referer = request.META.get("HTTP_REFERER")
    if referer and url_has_allowed_host_and_scheme(
        referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return referer
    return reverse("home")


@ratelimit(key="ip", rate="5/m", block=False)
def subscribe(request):
    redirect_to = _safe_redirect_target(request)

    if request.method == "POST":
        if getattr(request, "limited", False):
            messages.error(request, "Too many attempts — please wait a minute and try again.")
            return redirect(redirect_to)

        form = SubscribeForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            subscriber, created = Subscriber.objects.filter(email__iexact=email).first(), False
            if subscriber is None:
                subscriber = Subscriber.objects.create(email=email)
                created = True

            if created:
                messages.success(request, "You're subscribed! Thanks for joining.")
            elif not subscriber.is_active:
                subscriber.is_active = True
                subscriber.unsubscribed_at = None
                subscriber.save(update_fields=["is_active", "unsubscribed_at"])
                messages.success(request, "Welcome back — your subscription has been reactivated!")
            else:
                messages.info(request, "That email is already subscribed — you're all set.")
        else:
            # Surface the actual validation problem (e.g. malformed address)
            # instead of a generic message.
            email_errors = form.errors.get("email")
            messages.error(
                request,
                email_errors[0] if email_errors else "Please enter a valid email address.",
            )

    return redirect(redirect_to)


def unsubscribe(request, token):
    subscriber = get_object_or_404(Subscriber, unsubscribe_token=token)
    subscriber.is_active = False
    from django.utils import timezone
    subscriber.unsubscribed_at = timezone.now()
    subscriber.save(update_fields=["is_active", "unsubscribed_at"])
    return render(request, "newsletter/unsubscribed.html", {"subscriber": subscriber})
