from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.urls import reverse
from django.http import Http404
from django.db.models import Count
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from main.models import (
    SiteProfile, Project, Dashboard, Certificate, Recommendation,
    Tools, Publication, Open_Roles, Roles, AboutStat, AboutPillar,
    SignatureOutcome, CVDocument, DownloadLog, PageView, custom_user,
)
from newsletter.models import Subscriber, Campaign
from newsletter.utils import send_campaign

from .decorators import staff_required
from .registry import SECTIONS
from .models import PasswordResetOTP
from .forms import (
    TailwindFormMixin, styled_modelform_factory,
    ProjectForm, ProjectLinkFormSet,
    DashboardForm, DashboardMetricFormSet, DashboardImageFormSet,
    SiteProfileForm, SiteHighlightFormSet,
    CampaignForm,
    PasswordResetRequestForm, OTPVerifyForm, SetNewPasswordForm,
)


class StyledAuthForm(TailwindFormMixin, AuthenticationForm):
    pass


class StyledPasswordChangeForm(TailwindFormMixin, PasswordChangeForm):
    pass


def login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("studio:home")

    form = StyledAuthForm(request, data=request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            user = form.get_user()
            if not user.is_staff:
                messages.error(request, "This account doesn't have Studio access.")
            else:
                login(request, user)
                next_url = request.GET.get("next") or reverse("studio:home")
                return redirect(next_url)

    return render(request, "studio/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("studio:login")


# ---------------------------------------------------------------
# Forgot password — OTP flow (request code -> verify code -> set new password)
# ---------------------------------------------------------------
PWRESET_SESSION_UID = "pwreset_uid"
PWRESET_SESSION_OTP_ID = "pwreset_otp_id"
PWRESET_SESSION_VERIFIED = "pwreset_verified"


def _clear_pwreset_session(request):
    for key in (PWRESET_SESSION_UID, PWRESET_SESSION_OTP_ID, PWRESET_SESSION_VERIFIED):
        request.session.pop(key, None)


def password_reset_request(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("studio:home")

    form = PasswordResetRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip().lower()
        user = custom_user.objects.filter(email__iexact=email, is_staff=True).first()

        # Always show the same message whether or not an account exists,
        # so this page can't be used to find out who has Studio access.
        generic_message = "If that email has Studio access, a 6-digit code is on its way to it."

        if user is not None:
            if not settings.EMAIL_IS_CONFIGURED:
                messages.error(
                    request,
                    "Email isn't configured on this server yet, so a reset code can't be sent. "
                    "Add SMTP details to .env, or reset the password directly from the database."
                )
                return render(request, "studio/password_reset_request.html", {"form": form})

            otp = PasswordResetOTP.generate_for(user)
            try:
                send_mail(
                    subject="Your Studio password reset code",
                    message=(
                        f"Your Studio password reset code is: {otp.code}\n\n"
                        f"This code expires in {PasswordResetOTP.TTL_MINUTES} minutes. "
                        "If you didn't request this, you can safely ignore this email."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                request.session[PWRESET_SESSION_UID] = user.pk
                request.session[PWRESET_SESSION_OTP_ID] = otp.pk
                messages.success(request, generic_message)
                return redirect("studio:password_reset_verify")
            except Exception:
                messages.error(request, "Couldn't send the email right now — please try again shortly.")
                return render(request, "studio/password_reset_request.html", {"form": form})

        messages.success(request, generic_message)
        return redirect("studio:password_reset_request")

    return render(request, "studio/password_reset_request.html", {"form": form})


def password_reset_verify(request):
    uid = request.session.get(PWRESET_SESSION_UID)
    otp_id = request.session.get(PWRESET_SESSION_OTP_ID)
    if not uid or not otp_id:
        messages.error(request, "Start by entering your email again.")
        return redirect("studio:password_reset_request")

    otp = PasswordResetOTP.objects.filter(pk=otp_id, user_id=uid).first()
    if otp is None or not otp.is_valid:
        _clear_pwreset_session(request)
        messages.error(request, "That code has expired or is no longer valid — request a new one.")
        return redirect("studio:password_reset_request")

    form = OTPVerifyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if otp.verify(form.cleaned_data["code"]):
            request.session[PWRESET_SESSION_VERIFIED] = True
            return redirect("studio:password_reset_set_new")
        remaining = PasswordResetOTP.MAX_ATTEMPTS - otp.attempts
        if remaining <= 0:
            _clear_pwreset_session(request)
            messages.error(request, "Too many incorrect attempts — request a new code.")
            return redirect("studio:password_reset_request")
        messages.error(request, f"Incorrect code — {remaining} attempt(s) left.")

    return render(request, "studio/password_reset_verify.html", {"form": form})


def password_reset_set_new(request):
    uid = request.session.get(PWRESET_SESSION_UID)
    if not uid or not request.session.get(PWRESET_SESSION_VERIFIED):
        messages.error(request, "Please verify your code first.")
        return redirect("studio:password_reset_request")

    user = custom_user.objects.filter(pk=uid, is_staff=True).first()
    if user is None:
        _clear_pwreset_session(request)
        return redirect("studio:password_reset_request")

    form = SetNewPasswordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        new_password = form.cleaned_data["new_password1"]
        try:
            validate_password(new_password, user=user)
        except ValidationError as exc:
            for err in exc.messages:
                form.add_error("new_password1", err)
        else:
            user.set_password(new_password)
            user.save(update_fields=["password"])
            _clear_pwreset_session(request)
            # Multiple AUTHENTICATION_BACKENDS are configured (axes + the
            # standard model backend), so login() can't infer which one to
            # attach to this user on its own — we bypassed authenticate()
            # entirely since they already proved identity via the OTP.
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, "Password reset — you're now signed in.")
            return redirect("studio:home")

    return render(request, "studio/password_reset_set_new.html", {"form": form})


# ---------------------------------------------------------------
# Change password (while already logged in)
# ---------------------------------------------------------------
@staff_required
def password_change(request):
    if request.method == "POST":
        form = StyledPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # keep the current session logged in
            messages.success(request, "Password changed successfully.")
            return redirect("studio:profile_edit")
    else:
        form = StyledPasswordChangeForm(user=request.user)
    return render(request, "studio/password_change.html", {"form": form})


@staff_required
def home(request):
    # ── Content counts ────────────────────────────────────────────
    stats = {
        "Projects":           Project.objects.count(),
        "Dashboards":         Dashboard.objects.count(),
        "Certificates":       Certificate.objects.count(),
        "Recommendations":    Recommendation.objects.count(),
        "Technologies":       Tools.objects.count(),
        "Publications":       Publication.objects.count(),
        "Subscribers":        Subscriber.objects.filter(is_active=True).count(),
        "Open Roles":         Open_Roles.objects.count(),
        "Job Titles":         Roles.objects.count(),
        "About Stats":        AboutStat.objects.count(),
        "About Pillars":      AboutPillar.objects.count(),
        "Sig. Outcomes":      SignatureOutcome.objects.count(),
    }

    # ── Analytics ─────────────────────────────────────────────────
    cv_downloads_total       = DownloadLog.objects.filter(file_type='cv').count()
    project_downloads_total  = DownloadLog.objects.filter(file_type='project_pdf').count()
    total_page_views         = PageView.objects.count()
    top_pages = (
        PageView.objects
        .values('path')
        .annotate(views=Count('id'))
        .order_by('-views')[:8]
    )
    recent_downloads = DownloadLog.objects.select_related().order_by('-downloaded_at')[:10]
    # Per-project PDF download counts
    project_download_counts = (
        DownloadLog.objects
        .filter(file_type='project_pdf')
        .values('object_title')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    return render(request, "studio/home.html", {
        "stats":                    stats,
        "cv_downloads_total":       cv_downloads_total,
        "project_downloads_total":  project_downloads_total,
        "total_page_views":         total_page_views,
        "top_pages":                top_pages,
        "recent_downloads":         recent_downloads,
        "project_download_counts":  project_download_counts,
    })



def _get_section(key):
    section = SECTIONS.get(key)
    if not section:
        raise Http404("Unknown section")
    return section


@staff_required
def generic_list(request, section_key):
    section = _get_section(section_key)
    model = section["model"]
    if _has_field(model, "order"):
        objects = model.objects.all().order_by("order")
    else:
        objects = model.objects.all().order_by("-pk")

    q = request.GET.get("q", "").strip()
    if q:
        from django.db.models import Q
        search_q = Q()
        has_terms = False
        for col, _ in section["list_columns"]:
            if not _is_text_field(model, col):
                continue
            search_q |= Q(**{f"{col}__icontains": q})
            has_terms = True
        if has_terms:
            try:
                objects = objects.filter(search_q)
            except Exception:
                pass

    return render(request, "studio/generic_list.html", {
        "section_key": section_key, "section": section, "objects": objects, "q": q,
    })


def _has_field(model, name):
    try:
        model._meta.get_field(name)
        return True
    except Exception:
        return False


def _is_text_field(model, name):
    from django.db import models as dj_models
    try:
        field = model._meta.get_field(name)
    except Exception:
        return False
    return isinstance(field, (dj_models.CharField, dj_models.TextField, dj_models.SlugField, dj_models.EmailField, dj_models.URLField))


@staff_required
def generic_create(request, section_key):
    section = _get_section(section_key)
    FormClass = styled_modelform_factory(section["model"], section["fields"])
    form = FormClass(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f'{section["singular"]} created.')
        return redirect("studio:generic_list", section_key=section_key)
    return render(request, "studio/generic_form.html", {
        "section_key": section_key, "section": section, "form": form, "is_new": True,
    })


@staff_required
def generic_update(request, section_key, pk):
    section = _get_section(section_key)
    try:
        obj = section["model"].objects.get(pk=pk)
    except section["model"].DoesNotExist:
        messages.error(request, f'This {section["singular"]} does not exist or was already deleted.')
        return redirect("studio:generic_list", section_key=section_key)
    FormClass = styled_modelform_factory(section["model"], section["fields"])
    form = FormClass(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f'{section["singular"]} updated.')
        return redirect("studio:generic_list", section_key=section_key)
    return render(request, "studio/generic_form.html", {
        "section_key": section_key, "section": section, "form": form, "obj": obj, "is_new": False,
    })


@staff_required
def generic_delete(request, section_key, pk):
    section = _get_section(section_key)
    try:
        obj = section["model"].objects.get(pk=pk)
    except section["model"].DoesNotExist:
        messages.error(request, f'This {section["singular"]} does not exist or was already deleted.')
        return redirect("studio:generic_list", section_key=section_key)
    if request.method == "POST":
        obj.delete()
        messages.success(request, f'{section["singular"]} deleted.')
        next_url = request.POST.get("next")
        if next_url:
            return redirect(next_url)
        return redirect("studio:generic_list", section_key=section_key)
    
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER", "")
    return render(request, "studio/confirm_delete.html", {
        "section_key": section_key, "section": section, "obj": obj, "next_url": next_url,
    })


@staff_required
def project_list(request):
    projects = Project.objects.all()
    return render(request, "studio/project_list.html", {"projects": projects})


@staff_required
def project_create(request):
    form = ProjectForm(request.POST or None, request.FILES or None)
    formset = ProjectLinkFormSet(request.POST or None, instance=Project())
    if request.method == "POST" and form.is_valid():
        project = form.save()
        formset = ProjectLinkFormSet(request.POST, instance=project)
        if formset.is_valid():
            formset.save()
            messages.success(request, "Project created.")
            return redirect("studio:project_list")
    return render(request, "studio/project_form.html", {"form": form, "formset": formset, "project": None})


@staff_required
def project_update(request, pk):
    project = get_object_or_404(Project, pk=pk)
    form = ProjectForm(request.POST or None, request.FILES or None, instance=project)
    formset = ProjectLinkFormSet(request.POST or None, instance=project)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        form.save()
        formset.save()
        messages.success(request, "Project updated.")
        return redirect("studio:project_list")
    return render(request, "studio/project_form.html", {"form": form, "formset": formset, "project": project})


@staff_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        project.delete()
        messages.success(request, "Project deleted.")
        next_url = request.POST.get("next")
        if next_url:
            return redirect(next_url)
        return redirect("studio:project_list")
        
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER", "")
    return render(request, "studio/confirm_delete.html", {
        "section_key": "projects", "section": {"label": "Projects", "singular": "Project"}, "obj": project, "next_url": next_url,
    })


@staff_required
def dashboard_list(request):
    dashboards = Dashboard.objects.all()
    return render(request, "studio/dashboard_list.html", {"dashboards": dashboards})


@staff_required
def dashboard_create(request):
    form = DashboardForm(request.POST or None, request.FILES or None)
    formset = DashboardMetricFormSet(request.POST or None, instance=Dashboard())
    gallery_formset = DashboardImageFormSet(request.POST or None, request.FILES or None, instance=Dashboard())
    if request.method == "POST" and form.is_valid():
        dashboard = form.save()
        formset = DashboardMetricFormSet(request.POST, instance=dashboard)
        gallery_formset = DashboardImageFormSet(request.POST, request.FILES, instance=dashboard)
        if formset.is_valid() and gallery_formset.is_valid():
            formset.save()
            gallery_formset.save()
            messages.success(request, "Dashboard created.")
            return redirect("studio:dashboard_list")
    return render(request, "studio/dashboard_form.html", {
        "form": form, "formset": formset, "gallery_formset": gallery_formset, "dashboard": None,
    })


@staff_required
def dashboard_update(request, pk):
    dashboard = get_object_or_404(Dashboard, pk=pk)
    form = DashboardForm(request.POST or None, request.FILES or None, instance=dashboard)
    formset = DashboardMetricFormSet(request.POST or None, instance=dashboard)
    gallery_formset = DashboardImageFormSet(request.POST or None, request.FILES or None, instance=dashboard)
    if request.method == "POST" and form.is_valid() and formset.is_valid() and gallery_formset.is_valid():
        form.save()
        formset.save()
        gallery_formset.save()
        messages.success(request, "Dashboard updated.")
        return redirect("studio:dashboard_list")
    return render(request, "studio/dashboard_form.html", {
        "form": form, "formset": formset, "gallery_formset": gallery_formset, "dashboard": dashboard,
    })


@staff_required
def dashboard_delete(request, pk):
    dashboard = get_object_or_404(Dashboard, pk=pk)
    if request.method == "POST":
        dashboard.delete()
        messages.success(request, "Dashboard deleted.")
        next_url = request.POST.get("next")
        if next_url:
            return redirect(next_url)
        return redirect("studio:dashboard_list")
        
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER", "")
    return render(request, "studio/confirm_delete.html", {
        "section_key": "dashboards", "section": {"label": "Dashboards", "singular": "Dashboard"}, "obj": dashboard, "next_url": next_url,
    })



@staff_required
def profile_edit(request):
    profile = SiteProfile.objects.first()
    form = SiteProfileForm(request.POST or None, request.FILES or None, instance=profile)
    formset = SiteHighlightFormSet(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        form.save()
        formset.save()
        messages.success(request, "Site profile updated.")
        return redirect("studio:profile_edit")
    return render(request, "studio/profile_form.html", {"form": form, "formset": formset, "profile": profile})


@staff_required
def subscriber_list(request):
    subscribers = Subscriber.objects.all()
    return render(request, "studio/subscriber_list.html", {"subscribers": subscribers})


@staff_required
def subscriber_toggle(request, pk):
    subscriber = get_object_or_404(Subscriber, pk=pk)
    if request.method == "POST":
        subscriber.is_active = not subscriber.is_active
        subscriber.save(update_fields=["is_active"])
    return redirect("studio:subscriber_list")


@staff_required
def subscriber_delete(request, pk):
    subscriber = get_object_or_404(Subscriber, pk=pk)
    if request.method == "POST":
        subscriber.delete()
        messages.success(request, "Subscriber removed.")
        next_url = request.POST.get("next")
        if next_url:
            return redirect(next_url)
        return redirect("studio:subscriber_list")
        
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER", "")
    return render(request, "studio/confirm_delete.html", {
        "section_key": "subscribers", "section": {"label": "Subscribers", "singular": "Subscriber"}, "obj": subscriber, "next_url": next_url,
    })

@staff_required
def campaign_list(request):
    campaigns = Campaign.objects.all()
    return render(request, "studio/campaign_list.html", {
        "campaigns": campaigns,
        "email_backend": settings.EMAIL_BACKEND,
    })


@staff_required
def campaign_send_test(request):
    """Send a one-off test email to the logged-in Studio user so they can
    confirm SMTP is actually working before sending a real campaign."""
    if request.method == "POST":
        if not settings.EMAIL_IS_CONFIGURED:
            messages.warning(
                request,
                "Add EMAIL_HOST, EMAIL_HOST_USER and EMAIL_HOST_PASSWORD to your .env file first."
            )
        elif not request.user.email:
            messages.error(request, "Your Studio account has no email address to send a test to.")
        else:
            try:
                send_mail(
                    subject="Studio test email",
                    message="If you're reading this, your email settings are working correctly.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[request.user.email],
                    fail_silently=False,
                )
                messages.success(request, f"Test email sent to {request.user.email}.")
            except Exception as exc:
                messages.error(request, f"Couldn't send the test email: {exc}")
    return redirect("studio:campaign_list")


@staff_required
def campaign_create(request):
    form = CampaignForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Campaign saved as a draft. Send it from the Campaigns list when ready.")
        return redirect("studio:campaign_list")
    return render(request, "studio/campaign_form.html", {"form": form})


@staff_required
def campaign_send(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    if request.method == "POST":
        if campaign.is_sent:
            messages.warning(request, "That campaign was already sent.")
        elif not Subscriber.objects.filter(is_active=True, is_confirmed=True).exists():
            messages.warning(request, "No active subscribers to send to yet.")
        else:
            result = send_campaign(campaign, request=request)
            if not result.email_configured:
                messages.warning(
                    request,
                    f"Campaign marked as sent to {result.sent} subscriber(s), but email isn't "
                    "configured yet — nothing actually left the server. Add SMTP details in your "
                    ".env file to send for real."
                )
            elif result.all_failed:
                messages.error(
                    request,
                    f"Delivery failed for all {result.total} subscriber(s) — check your SMTP "
                    "settings in .env and try again."
                )
            elif result.failed:
                messages.warning(
                    request,
                    f"Sent to {result.sent} of {result.total} subscriber(s) — "
                    f"{result.failed} failed to deliver."
                )
            else:
                messages.success(request, f"Sent to {result.sent} subscriber(s).")
    return redirect("studio:campaign_list")


@staff_required
def reset_analytics(request):
    """Clear the download/page-view logs that back the Studio dashboard
    figures. This is a destructive, irreversible action — POST only,
    confirmed on the frontend before submit."""
    if request.method == "POST":
        scope = request.POST.get("scope", "all")
        deleted = 0
        if scope in ("all", "downloads"):
            deleted += DownloadLog.objects.all().delete()[0]
        if scope in ("all", "views"):
            deleted += PageView.objects.all().delete()[0]
        messages.success(request, f"Analytics reset — cleared {deleted} record(s).")
    return redirect("studio:home")
