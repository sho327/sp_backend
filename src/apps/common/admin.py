from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from apps.common.models import T_FileResource
from django.db.models import Q

# 共通Mixin
class SaveAdminMixin:
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
            obj.created_method = "admin_panel"
        obj.updated_by = request.user
        obj.updated_method = "admin_panel"
        super().save_model(request, obj, form, change)
    
    # SHOW_VIEW_ON_SITEがTrueの場合だけ設定される
        def view_on_site(self, obj):
            return "http://localhost:3000/dashboard"

class SoftDeleteFilter(admin.SimpleListFilter):
    title = _('状態')
    parameter_name = 'is_deleted'
    def lookups(self, request, model_admin):
        return (('active', _('有効のみ')), ('deleted', _('削除済みのみ')),)
    def queryset(self, request, queryset):
        if self.value() == 'active': return queryset.filter(deleted_at__isnull=True)
        if self.value() == 'deleted': return queryset.filter(deleted_at__isnull=False)
        return queryset

# ------------------------------------------------------------------
# T_FileResource
# ------------------------------------------------------------------
@admin.register(T_FileResource)
class T_FileResourceAdmin(SaveAdminMixin, ModelAdmin):
    list_display = ("file_name", "file_type", "display_preview", "file_size_kb", "created_at", "deleted_at")
    list_filter = (SoftDeleteFilter, "file_type", "deleted_at")
    search_fields = ("file_name", "external_url")
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        ("基本情報", {"fields": ("id", "file_name", "file_type")}),
        ("リソース実体", {"fields": ("file_data", "external_url", "file_size")}),
        ("システム情報", {
            "fields": ("created_method", "updated_method", "created_at", "updated_at", "deleted_at"),
            "classes": ("collapse",)
        }),
    )

    def display_preview(self, obj):
        """管理画面上で画像のプレビューを表示"""
        # ※ モデル側に url プロパティがある前提です
        if hasattr(obj, 'url') and obj.url:
            return format_html('<img src="{}" style="width: 50px; height: auto; border-radius: 4px;" />', obj.url)
        return "-"
    display_preview.short_description = "プレビュー"

    def file_size_kb(self, obj):
        """バイト表記をKB表記に変換して表示"""
        if obj.file_size:
            return f"{round(obj.file_size / 1024, 2)} KB"
        return "-"
    file_size_kb.short_description = "サイズ"

    # def get_queryset(self, request):
    #     qs = super().get_queryset(request)
    #     if request.user.is_superuser:
    #         return qs
    #     # 一般スタッフは自分に紐づくデータのみ表示
    #     return qs.filter(
    #         Q(icon_t_profile_set=request.user) | 
    #         Q(external_icon_t_artist_set=request.user) | 
    #         Q(image_t_playlist_set=request.user)
    #     )