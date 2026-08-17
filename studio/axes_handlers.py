from django.shortcuts import redirect
from django.contrib import messages

def lockout(request, credentials=None, *args, **kwargs):
    messages.error(
        request,
        "Too many failed login attempts. Try again in 1 hour."
    )
    return redirect("studio:login")