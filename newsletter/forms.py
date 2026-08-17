from django import forms
from .models import Subscriber


class SubscribeForm(forms.ModelForm):
    class Meta:
        model = Subscriber
        fields = ["email"]
        widgets = {
            "email": forms.EmailInput(attrs={
                "placeholder": "you@example.com",
                "class": "subscribe-input",
                "required": "required",
            })
        }

    def clean_email(self):
        # Normalise (EmailField already validates the format itself, so if
        # we get here the address is well-formed). We deliberately do NOT
        # enforce the model's unique constraint here — the view decides
        # what "already subscribed" should mean (new / reactivate / already
        # active) so it can show the right message instead of a generic
        # form error.
        return self.cleaned_data["email"].strip().lower()

    def validate_unique(self):
        # Skip ModelForm's automatic uniqueness check on `email`. Without
        # this, an already-subscribed address makes the whole form invalid
        # before the view ever gets a chance to say "you're already on the
        # list" — it just falls through to a misleading
        # "enter a valid email" error instead.
        pass
