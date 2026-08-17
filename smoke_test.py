import os, django, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
django.setup()

from django.test.utils import setup_test_environment
setup_test_environment()  # allows the 'testserver' host used by django.test.Client

from django.test import Client
from main.models import custom_user, Project, Dashboard, Publication, Certificate

c = Client()
results = []

def hit(method, url, data=None, follow=False, expect=None):
    try:
        if method == "get":
            r = c.get(url, follow=follow)
        else:
            r = c.post(url, data or {}, follow=follow)
        status = r.status_code
        ok = (status < 400) if expect is None else (status == expect)
        results.append((ok, method.upper(), url, status))
        if not ok:
            print(f"FAIL {method.upper()} {url} -> {status}")
    except Exception as e:
        results.append((False, method.upper(), url, f"EXC: {e}"))
        print(f"EXCEPTION {method.upper()} {url} -> {e}")

# ── Public pages ──
hit("get", "/")
hit("get", "/projects/")
hit("get", "/dashboards/")
hit("get", "/research/")
hit("get", "/certificates/")
hit("get", "/recommendations/")
hit("get", "/activity/")
hit("get", "/contact/")
hit("get", "/cv_view/")
hit("get", "/search/?q=data")
hit("get", "/nonexistent-page-xyz/", expect=404)

p = Project.objects.filter(status="published").first()
if p:
    hit("get", f"/projects/{p.slug}/")
d = Dashboard.objects.filter(is_published=True).first()
if d:
    hit("get", f"/dashboards/{d.slug}/")
pub = Publication.objects.filter(is_published=True).first()
if pub:
    hit("get", f"/research/{pub.slug}/")

# ── Newsletter ──
hit("post", "/newsletter/subscribe/", {"email": "smoketest_new@example.com"}, follow=True)
hit("post", "/newsletter/subscribe/", {"email": "smoketest_new@example.com"}, follow=True)  # duplicate
hit("post", "/newsletter/subscribe/", {"email": "not-an-email"}, follow=True)  # invalid

# ── Studio (unauthenticated) ──
hit("get", "/studio/", expect=302)
hit("get", "/studio/login/")
hit("get", "/studio/password-reset/")
hit("get", "/studio/password-change/", expect=302)  # not logged in -> redirected to login
hit("get", "/admin/", expect=404)
hit("get", "/admin/login/", expect=404)

# ── Studio (authenticated) ──
user = custom_user.objects.filter(is_staff=True).first()
if user:
    c.force_login(user)
    hit("get", "/studio/")
    hit("get", "/studio/profile/")
    hit("get", "/studio/projects/")
    hit("get", "/studio/dashboards/")
    hit("get", "/studio/campaigns/")
    hit("get", "/studio/campaigns/add/")
    hit("get", "/studio/subscribers/")
    hit("get", "/studio/technologies/")
    hit("get", "/studio/certificates/")
    hit("get", "/studio/recommendations/")
    hit("get", "/studio/research/")
    hit("get", "/studio/cv/")
    hit("get", "/studio/downloads/")
    hit("get", "/studio/open-roles/")
    hit("get", "/studio/job-titles/")
    hit("get", "/studio/about-stats/")
    hit("get", "/studio/about-pillars/")
    hit("get", "/studio/signature-outcomes/")
    hit("get", "/studio/connect-links/")
    hit("get", "/studio/categories/")
    hit("get", "/studio/projects/add/")
    hit("get", "/studio/dashboards/add/")
    hit("get", "/studio/password-change/")
    hit("get", "/admin/")
else:
    print("No staff user found — skipping authenticated studio checks")

print("\n--- SUMMARY ---")
failed = [r for r in results if not r[0]]
print(f"{len(results)-len(failed)}/{len(results)} passed")
for r in failed:
    print("FAILED:", r)
