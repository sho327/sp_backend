from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from apps.artist.models import M_ArtistTag, M_ArtistContext, T_Artist, R_ArtistTag

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
    # def view_on_site(self, obj):
    #     return "http://localhost:3000/dashboard"

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
# Inline
# ------------------------------------------------------------------
# class R_ArtistTagInline(TabularInline):
#     model = R_ArtistTag
#     extra = 1
#     fields = ("tag", "created_at")
#     readonly_fields = ("created_at",)

# ------------------------------------------------------------------
# マスタ系
# ------------------------------------------------------------------
@admin.register(M_ArtistTag)
class M_ArtistTagAdmin(SaveAdminMixin, ModelAdmin):
    list_display = ("name", "created_at", "deleted_at")
    search_fields = ("name",)
    list_filter = (SoftDeleteFilter, "deleted_at")
    ordering = ("name",)
    # 管理者でも名前変更のみ許可する
    readonly_fields = (
        "created_method",
        "updated_method", 
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        # "deleted_at",
    )
    # 整合性が取れないので、削除禁止
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(M_ArtistContext)
class M_ArtistContextAdmin(SaveAdminMixin, ModelAdmin):
    list_display = ("name", "created_at", "deleted_at")
    search_fields = ("name",)
    list_filter = (SoftDeleteFilter, "deleted_at")
    ordering = ("name",)
    # 管理者でも名前変更のみ許可する
    readonly_fields = (
        "created_method",
        "updated_method", 
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        # "deleted_at",
    )
    # 整合性が取れないので、削除禁止
    def has_delete_permission(self, request, obj=None):
        return False

# # ------------------------------------------------------------------
# # T_Artist
# # ------------------------------------------------------------------
# @admin.register(T_Artist)
# class T_ArtistAdmin(SaveAdminMixin, ModelAdmin):
#     list_display = ("name", "user", "deezer_id", "context", "created_at", "deleted_at")
#     list_filter = (SoftDeleteFilter, "context", "user", "deleted_at")
#     search_fields = ("name", "deezer_id", "user__user_id_display", "user__display_name")
#     readonly_fields = ("id", "created_at", "updated_at")
#     inlines = [R_ArtistTagInline]

#     fieldsets = (
#         (None, {"fields": ("id", "user")}),
#         ("基本情報", {"fields": ("name", "deezer_id", "deezer_image")}),
#         ("SetlistFm連携情報", {"fields": ("setlistfm_mbid", "is_mbid_autoset")}),
#         ("分類・背景", {"fields": ("context",)}),
#         ("システム情報", {
#             "fields": ("created_method", "updated_method", "created_at", "updated_at", "deleted_at"),
#             "classes": ("collapse",)
#         }),
#     )

# ------------------------------------------------------------------
# R_ArtistTag
# ------------------------------------------------------------------
# @admin.register(R_ArtistTag)
# class R_ArtistTagAdmin(SaveAdminMixin, ModelAdmin):
#     list_display = ("artist", "tag", "created_at")
#     list_filter = (SoftDeleteFilter, )
#     search_fields = ("artist__name", "tag__name")
#     readonly_fields = ("created_at", "updated_at")