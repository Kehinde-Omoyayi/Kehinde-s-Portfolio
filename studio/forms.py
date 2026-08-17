from django import forms
from django.forms import inlineformset_factory

from main.models import (
    Project, ProjectLink, Dashboard, DashboardMetric, DashboardImage, Dataset,
    SiteProfile, Currently_Focused,
)
from newsletter.models import Campaign


TEXT_CLASSES = (
    "w-full rounded-lg bg-[#0f1420] border border-white/15 text-gray-100 "
    "px-3 py-2 text-sm focus:outline-none focus:border-accent"
)
SELECT_CLASSES = TEXT_CLASSES
CHECKBOX_CLASSES = "h-4 w-4 rounded border-white/30 bg-[#0f1420] text-accent focus:ring-accent"
FILE_CLASSES = "w-full text-sm text-gray-300 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:bg-accent file:text-white file:text-sm"


class TailwindFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            if field is None:
                raise Exception(f"{name} is None")

            widget = field.widget

            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = CHECKBOX_CLASSES
            elif isinstance(widget, forms.ClearableFileInput):
                widget.attrs["class"] = FILE_CLASSES
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = SELECT_CLASSES
                if isinstance(widget, forms.SelectMultiple):
                    widget.attrs["size"] = 6
            elif isinstance(widget, forms.Textarea):
                widget.attrs["class"] = TEXT_CLASSES
                widget.attrs.setdefault("rows", 5)
            else:
                widget.attrs["class"] = TEXT_CLASSES


def styled_modelform_factory(model, fields):
    base = forms.modelform_factory(model, fields=fields)
    return type(f"Styled{model.__name__}Form", (TailwindFormMixin, base), {})


# ---------------------------------------------------------------
# PROJECT (+ up to 3 ProjectLinks)
# ---------------------------------------------------------------

class ProjectForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "name", "summary", "description", "cover_image",
            "categories", "technologies",
            "pdf_report", "allow_pdf_download",
            "is_featured", "status", "order",
        ]



class ProjectLinkInlineForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = ProjectLink
        fields = ["link_type", "url", "label", "order"]


ProjectLinkFormSet = inlineformset_factory(
    Project, ProjectLink, form=ProjectLinkInlineForm,
    fields=["link_type", "url", "label", "order"],
    extra=1, max_num=3, validate_max=True, can_delete=True,
)


# ---------------------------------------------------------------
# DASHBOARD (+ DashboardMetrics)
# ---------------------------------------------------------------

class DashboardForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Dashboard
        fields = [
            "title", "description", "thumbnail",
            "embed_type", "embed_url",
            "categories", "technologies", "external_url",
            "related_project", "related_datasets",
            "is_featured", "is_published", "order",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["related_project"].required = False
        self.fields["related_project"].empty_label = "— No linked project —"
        self.fields["related_datasets"].required = False
        # If a project is already chosen (editing an existing dashboard),
        # narrow the dataset choices to that project's own datasets first —
        # still shows everything, just ordered so relevant ones are on top.
        self.fields["related_datasets"].queryset = Dataset.objects.all()


class DashboardMetricInlineForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = DashboardMetric
        fields = ["label", "value", "order"]


DashboardMetricFormSet = inlineformset_factory(
    Dashboard, DashboardMetric, form=DashboardMetricInlineForm,
    fields=["label", "value", "order"],
    extra=1, can_delete=True,
)


class DashboardImageInlineForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = DashboardImage
        fields = ["image", "caption", "order"]


DashboardImageFormSet = inlineformset_factory(
    Dashboard, DashboardImage, form=DashboardImageInlineForm,
    fields=["image", "caption", "order"],
    extra=2, can_delete=True,
)


# ---------------------------------------------------------------
# SITE PROFILE (+ SiteHighlights) — singleton
# ---------------------------------------------------------------

class SiteProfileForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = SiteProfile
        fields = [
            "full_name", "headline", "role_titles", "short_bio", "profile_picture",
            "about_me", "availability_status", "open_to_roles", "active_cv",
        ]


class SiteHighlightInlineForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Currently_Focused
        fields = ["text", "order"]


SiteHighlightFormSet = inlineformset_factory(
    SiteProfile,Currently_Focused, form=SiteHighlightInlineForm,
    fields=["text", "order"],
    extra=1, can_delete=True,
)


# ---------------------------------------------------------------
# NEWSLETTER CAMPAIGN
# ---------------------------------------------------------------

class CampaignForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ["subject", "body_html"]
        widgets = {
            "body_html": forms.Textarea(attrs={"rows": 10}),
        }


# ---------------------------------------------------------------
# AUTH — forgot password (OTP) + change password while logged in
# ---------------------------------------------------------------

class PasswordResetRequestForm(TailwindFormMixin, forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com", "autofocus": "autofocus"})
    )


class OTPVerifyForm(TailwindFormMixin, forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            "placeholder": "6-digit code",
            "inputmode": "numeric",
            "autocomplete": "one-time-code",
            "autofocus": "autofocus",
        }),
    )


class SetNewPasswordForm(TailwindFormMixin, forms.Form):
    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(attrs={"autofocus": "autofocus", "autocomplete": "new-password"}),
    )
    new_password2 = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("new_password1"), cleaned.get("new_password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Those two passwords don't match.")
        return cleaned
