import re

from django.db import models
from django.contrib.auth.models import AbstractBaseUser,PermissionsMixin,BaseUserManager
from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.templatetags.static import static

#customising the admin to function with email and password instead of the traditional username
class custom_user_manager(BaseUserManager):
    def create_user (self, email, first_name, last_name, password=None):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name, last_name=last_name)
        user.set_password(password)
        user.save(using = self.db)
        return user
    def create_superuser(self, email, first_name, last_name, password):
        user = self.create_user(email, first_name, last_name, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self.db)
        return user

#customised based user in continuity to the user
class custom_user(AbstractBaseUser,PermissionsMixin):
    first_name = models.CharField(max_length=40)
    last_name = models.CharField(max_length=40)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = custom_user_manager()

    def __str__(self):
        return f'{self.email}'
    

# ====================================================================
class Category(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True, blank=True) #for the url display (example.com/category/data-analytics/) instead of something like (example.com/category/3/)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    # in case slug wasn't written it covert's some like data analysis to data-analysis for the url (using 'from django.utils.text import slugify')
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# ====================================================================
class Tools(models.Model):
    name = models.CharField(max_length=60, unique=True)
    icon_image = models.ImageField( upload_to="tools_pics", blank=True, null=True)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    
    def __str__(self):
        return self.name

# ====================================================================
class Connect_Link(models.Model):
    PLATFORM_CHOICES = [
        ("linkedin", "LinkedIn"),
        ("github", "GitHub"),
        ("email", "Email"),
        ("twitter", "X / Twitter"),
        ("instagram", "Instagram"),
        ("facebook", "Facebook"),
        ("youtube", "YouTube"),
        ("whatsapp", "WhatsApp"),
        ("website", "Other website"),
    ]
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    # NOTE: intentionally a CharField, not a URLField. This holds a real
    # URL for most platforms, but a bare email address for "email" and a
    # bare phone number/handle for "whatsapp" - a URLField would silently
    # rewrite something like "me@example.com" into "http://me@example.com"
    # the moment it passed through a ModelForm, breaking the mailto: link
    # built below.
    url_or_handle = models.CharField(max_length=200, blank=True)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["platform"]

    def __str__(self):
        return f"{self.get_platform_display()}"

    @property       #for specifically  my email and whatsapp because the url is not direct 
    def href(self):
        if self.platform == "email":
            # Defensive: older data may have been saved back when this
            # field was a URLField and got an "http://" prefix forced
            # onto a bare email address.
            value = re.sub(r"^https?://", "", self.url_or_handle or "")
            return f"mailto:{value}"
        if self.platform == "whatsapp" and not self.url_or_handle.startswith("http"):
            return f"https://wa.me/{self.url_or_handle}"
        return self.url_or_handle

    @property
    def Logo_Url(self): #to make sure the logo fur the exact link appears in the home page
        return static(f'platforms/{self.platform}.svg')

    def save(self, *args, **kwargs):
        if self.platform not in ["email", "whatsapp"]:
            if (
                self.url_or_handle
                and not self.url_or_handle.startswith(("http://", "https://"))
            ):
                self.url_or_handle = f"https://{self.url_or_handle}"

        super().save(*args, **kwargs)

# ====================================================================
class CVDocument(models.Model):
    title = models.CharField(max_length=120, default="Kehinde Omoyayi CV")
    file = models.FileField(upload_to="project/cv/")
    is_public = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "CV / Resume"

    def __str__(self):
        return f"{self.title}"


class Open_Roles(models.Model):
    roles = models.CharField(unique=True)

    def __str__(self):
        return self.roles

class Roles(models.Model):
    roles = models.CharField(max_length=100, unique=True) 

    def __str__(self):
        return str(self.roles) 


# ====================================================================
class SiteProfile(models.Model):
    full_name = models.CharField( max_length=120, default="Kehinde Omoyayi")
    headline = models.CharField( max_length=200, default="Turning Data Into Insights. Building Solutions. Creating Impact.")
    role_titles = models.ManyToManyField(Roles, blank=True)
    short_bio = models.TextField(default="I transform raw data into actionable insights, build scalable backend systems, and develop intelligent solutions to solve real world problems." )
    note = models.TextField(default= 'Most Analysts shows you what happened. I show you what to do next.')
    location = models.CharField(max_length=100, default="Nigeria")
    education = models.CharField(max_length=100, default="MSc. Data Science")
    experience_years = models.CharField(max_length=100, default="4+ Years Exp.")
    about_me = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to="profile/")
    story = models.TextField(blank=True)
    availability_status = models.CharField(max_length=25, default="Available for Discussion")
    open_to_roles = models.ManyToManyField(Open_Roles, blank=True)
    active_cv = models.ForeignKey( "CVDocument", on_delete=models.CASCADE, null=True, blank=True, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name



# ====================================================================
class Currently_Focused(models.Model): 
    profile = models.ForeignKey(SiteProfile, on_delete=models.CASCADE, related_name="highlights")
    text = models.CharField(max_length=120)
    icon_svg = models.FileField(upload_to="focus_icons/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.text


# ====================================================================
class Project(models.Model):
    STATUS_CHOICES = [("draft", "Draft"), ("published", "Published")]
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    summary = models.CharField(max_length=80)
    description = models.TextField()
    cover_image = models.ImageField(upload_to="projects/covers/", blank=True, null=True)
    categories = models.ManyToManyField(Category, blank=True, related_name="projects")
    technologies = models.ManyToManyField(Tools, blank=True, related_name="projects")
    pdf_report = models.FileField(upload_to="projects/pdfs/", blank=True, null=True)
    allow_pdf_download = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="published")
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse ("project_detail", kwargs={"slug": self.slug})

    @property
    def is_currently_featured(self):
        return self.is_featured


# ====================================================================
class ProjectLink(models.Model):
    LINK_TYPES = [
        ("github", "GitHub repository"),
        ("live_demo", "Live demo / app"),
        ("article", "Article / write-up"),
        ("video", "Video walkthrough"),
        ("other", "Other link"),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="links")
    link_type = models.CharField(max_length=20, choices=LINK_TYPES, default="github")
    url = models.URLField()
    label = models.CharField(max_length=60, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.project.name} -> {self.get_link_type_display()}"

    def clean(self):            # Enforce "up to 3 links" per project.
        if self.project_id:
            qs = ProjectLink.objects.filter(project_id=self.project_id).exclude(pk=self.pk)
            if qs.count() >= 3:
                raise ValidationError("Each project can have at most 3 external links.")

    @property
    def icon(self):
        return f"images/icons/{self.link_type}.svg"



# ====================================================================
class Dataset(models.Model):
    FILE_KIND_CHOICES = [("dataset", "Dataset"), ("report", "Report")]

    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    kind = models.CharField(max_length=10, choices=FILE_KIND_CHOICES, default="dataset")
    file = models.FileField(upload_to="project/dataset/")
    related_project = models.ForeignKey( Project, on_delete=models.CASCADE, blank=True, null=True, related_name="datasets_reports")
    is_public = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.title


# ====================================================================
class Dashboard(models.Model):
    EMBED_TYPES = [
        ("powerbi", "Power BI"),
        ("tableau", "Tableau Public"),
        ("iframe", "Other embeddable URL (generic iframe)"),
        ("image", "Static image only (no live embed)"),
    ]

    title = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    description = models.TextField(blank=True)
    thumbnail = models.ImageField(upload_to="project/dashboard/thumbnails/", blank=True, null=True)
    embed_type = models.CharField(max_length=10, choices=EMBED_TYPES, default="powerbi")
    embed_url = models.URLField(blank=True)
    categories = models.ManyToManyField(Category, blank=True, related_name="dashboards")
    technologies = models.ManyToManyField(Tools, blank=True, related_name="dashboards")
    external_url = models.URLField(blank=True) #Optional 'Open Dashboard' link if it lives outside your site too."
    related_project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, blank=True, null=True, related_name="dashboards",
        help_text="The project this dashboard was built for, if any.",
    )
    related_datasets = models.ManyToManyField(
        Dataset, blank=True, related_name="dashboards",
        help_text="Dataset(s)/report(s) that feed this dashboard.",
    )
    is_featured = models.BooleanField(default=True)
    is_published = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("dashboard_detail", kwargs={"slug": self.slug})


# ====================================================================
class DashboardImage(models.Model):
    """One extra screenshot in a dashboard's gallery — e.g. the home view,
    an event-details drilldown, a filter state, etc. — beyond the single
    `thumbnail` used for cards/previews."""
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name="gallery_images")
    image = models.ImageField(upload_to="project/dashboard/gallery/")
    caption = models.CharField(max_length=120, blank=True, help_text="e.g. 'Home view', 'Event details'")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.dashboard.title} — {self.caption or 'image'}"


# ====================================================================
class DashboardMetric(models.Model):    #One KPI tile shown above a dashboard, e.g. 'Coverage Rate: 65.7%'
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name="metrics")
    label = models.CharField(max_length=60)
    value = models.CharField(max_length=30, help_text="e.g. 65.7%  or  12.4M")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.dashboard.title}: {self.label} = {self.value}"


# ====================================================================
class Certificate(models.Model):
    title = models.CharField(max_length=150)
    issuing_organization = models.CharField(max_length=150)
    image = models.ImageField(upload_to="certificates/")
    credential_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    date_issued = models.DateField(blank=True, null=True)
    categories = models.ManyToManyField(Category, blank=True, related_name="certificate_cat")
    is_visible = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "-date_issued"]

    def __str__(self):
        return self.title


# ====================================================================
class Recommendation(models.Model):
    name = models.CharField(max_length=120)
    title_and_company = models.CharField(max_length=150, blank=True)    #Head of Analytics, Acme Ltd
    photo = models.ImageField(upload_to="recommendations/", blank=True, null=True)
    message = models.TextField()
    url = models.URLField(blank=True)
    is_visible = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self):
        return f"{self.name} - {self.title_and_company}" 



# ====================================================================

class Publication(models.Model):
    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=270, unique=True, blank=True)
    authors = models.CharField(max_length=300, blank=True)
    abstract = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to="research/cover/", blank=True, null=True)
    pdf_file = models.FileField(upload_to="research/pdfs/", blank=True, null=True)
    external_url = models.URLField(blank=True)
    categories = models.ManyToManyField(Category, blank=True, related_name="publications")
    publication_year = models.PositiveIntegerField(blank=True, null=True)
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("research_detail", args=[self.slug])



# ====================================================================

class AboutStat(models.Model):
    value = models.CharField(max_length=9)
    suffix = models.CharField(max_length=10, blank=True)
    label = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.value}{self.suffix} — {self.label}"


class AboutPillar(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


class SignatureOutcome(models.Model):
    stat = models.CharField(max_length=20, help_text="e.g. 18%, ₦7M, ₦500K+")
    title = models.CharField(max_length=150)
    detail = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.stat} — {self.title}"


# ====================================================================
class DownloadLog(models.Model):
    """Tracks every file download (CV, project PDF, dataset, etc.)."""
    FILE_TYPES = [
        ('cv',          'CV / Resume'),
        ('project_pdf', 'Project PDF'),
        ('dataset',     'Dataset / Report'),
        ('other',       'Other'),
    ]
    file_type    = models.CharField(max_length=30, choices=FILE_TYPES, default='other')
    object_id    = models.IntegerField(null=True, blank=True,
                                       help_text="PK of the related object (Project, CVDocument, etc.)")
    object_title = models.CharField(max_length=200, blank=True)
    ip_address   = models.GenericIPAddressField(null=True, blank=True)
    user_agent   = models.CharField(max_length=400, blank=True)
    downloaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-downloaded_at']
        verbose_name      = 'Download Log'
        verbose_name_plural = 'Download Logs'

    def __str__(self):
        return f"{self.get_file_type_display()} — {self.object_title} ({self.downloaded_at:%Y-%m-%d})"


# ====================================================================
class PageView(models.Model):
    """Lightweight page-view counter per path."""
    path        = models.CharField(max_length=300)
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    viewed_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-viewed_at']
        verbose_name      = 'Page View'
        verbose_name_plural = 'Page Views'

    def __str__(self):
        return f"{self.path} — {self.viewed_at:%Y-%m-%d %H:%M}"