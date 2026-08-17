from django.contrib import admin
from .models import *
from django.utils.html import format_html


def thumb(obj, field_name, height=40):
    file = getattr(obj, field_name, None)
    if file:
        return format_html('<img src="{}" style="height:{}px;border-radius:4px;" />', file.url, height)
    return "-"


class SiteHighlightInline(admin.TabularInline):
    model = Currently_Focused
    extra = 1


admin.site.register(SiteProfile)
admin.site.register(Roles)
admin.site.register(Currently_Focused)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Tools)
class ToolsAdmin(admin.ModelAdmin):
    list_display = ("name", "icon_preview", "is_visible")
    list_editable = ["is_visible"]
    search_fields = ("name",)

    def icon_preview(self, obj):
        return thumb(obj, "icon_image")
    icon_preview.short_description = "Icon"


@admin.register(Connect_Link)
class ConnectLinkAdmin(admin.ModelAdmin):
    list_display = ("platform", "url_or_handle", "is_visible")
    list_editable = [ "is_visible"]


class ProjectLinkInline(admin.TabularInline):
    model = ProjectLink
    extra = 1
    max_num = 3


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "cover_thumb", "name", "status", "is_featured", "allow_pdf_download", "order", "created_at",
    )
    list_editable = ("is_featured", "order")
    list_filter = ("status", "is_featured", "categories", "technologies")
    search_fields = ("name", "summary", "description")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("categories", "technologies")
    inlines = [ProjectLinkInline]
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "slug", "summary", "description", "cover_image")}),
        ("Tags", {"fields": ("categories", "technologies")}),
        ("PDF report", {"fields": ("pdf_report", "allow_pdf_download")}),
        ("Publishing", {"fields": ("status", "is_featured", "order")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def cover_thumb(self, obj):
        return thumb(obj, "cover_image", 40)
    cover_thumb.short_description = ""




@admin.register(CVDocument)
class CVDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "is_public", "uploaded_at")
    list_editable = ("is_public",)


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "related_project", "is_public", "uploaded_at")
    list_editable = ("is_public",)
    list_filter = ("kind", "is_public")
    search_fields = ("title", "description")


class DashboardMetricInline(admin.TabularInline):
    model = DashboardMetric
    extra = 1


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ("thumb_preview", "title", "embed_type", "is_featured", "is_published", "order")
    list_editable = ("is_featured", "is_published", "order")
    list_filter = ("embed_type", "is_featured", "is_published", "categories")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("categories", "technologies")
    inlines = [DashboardMetricInline]

    def thumb_preview(self, obj):
        return thumb(obj, "thumbnail", 40)
    thumb_preview.short_description = ""


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("image_preview", "title", "issuing_organization", "date_issued", "is_visible", "order")
    list_editable = ("is_visible", "order")
    search_fields = ("title", "issuing_organization")

    def image_preview(self, obj):
        return thumb(obj, "image", 40)
    image_preview.short_description = ""


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ("photo_preview", "name", "title_and_company", "is_visible", "order", "created_at")
    list_editable = ("is_visible", "order")
    search_fields = ("name", "title_and_company", "message")

    def photo_preview(self, obj):
        return thumb(obj, "photo", 40)
    photo_preview.short_description = ""


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ("title", "authors", "publication_year", "is_published", "published_at")
    list_editable = ("is_published",)
    list_filter = ("is_published", "categories", "publication_year")
    search_fields = ("title", "authors", "abstract")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("categories",)


admin.site.register(Open_Roles)
admin.site.register(AboutStat)
admin.site.register(AboutPillar)
admin.site.register(SignatureOutcome)
