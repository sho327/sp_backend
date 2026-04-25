from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin  # UnfoldのModelAdmin
from simple_history.admin import SimpleHistoryAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.account.models import M_User, T_UserToken, T_LoginHistory, T_Profile

# 1. 共通化用Mixin
class SaveAdminMixin:
    def save_model(self, request, obj, form, change):
        if not change:  # 新規作成時
            obj.created_by = request.user
            obj.created_method = "admin_panel"
        
        # 更新・新規共通
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
# M_User
# ------------------------------------------------------------------
@admin.register(M_User)
class M_UserAdmin(SaveAdminMixin, SimpleHistoryAdmin, ModelAdmin):
# class M_UserAdmin(SaveAdminMixin, BaseUserAdmin):
    list_display = ("email", "is_active", "is_staff", "is_superuser", "last_login", "created_at", "deleted_at")
    list_filter = (SoftDeleteFilter, "is_active", "is_staff", "is_superuser", "deleted_at")
    search_fields = ("email", )
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("権限", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("重要日時", {"fields": ("last_login", "created_at", "updated_at", "deleted_at")}),
        ("システム情報", {"fields": ("created_method", "updated_method")}),
    )
    readonly_fields = ("id", "last_login", "created_at", "created_method",  "updated_at")
    # 削除禁止
    def has_delete_permission(self, request, obj=None):
        return False

# ------------------------------------------------------------------
# T_Profile
# ------------------------------------------------------------------
# @admin.register(T_Profile)
# class T_ProfileAdmin(SaveAdminMixin, ModelAdmin):
#     list_display = ("user_id_display", "display_name", "status_code", "is_setup_completed", "updated_at", "deleted_at")
#     list_filter = (SoftDeleteFilter, "status_code", "is_setup_completed", "deleted_at")
#     search_fields = ("user_id_display", "display_name", "user__email")
#     readonly_fields = ("created_at", "updated_at")

# 管理者用としてステータスコード、ロック解除日時以外は触らせない
@admin.register(T_Profile)
class T_ProfileAdmin(SaveAdminMixin, SimpleHistoryAdmin, ModelAdmin):
    list_display = ("user_id_display", "display_name", "status_code", "is_setup_completed", "updated_at", "deleted_at")
    list_filter = (SoftDeleteFilter, "status_code", "is_setup_completed", "deleted_at")
    search_fields = ("user_id_display", "display_name", "user__email")
    readonly_fields = (
        "user",
        # "user_id_display",
        # "display_name", 
        # "affiliation",
        # "bio",
        # "icon", 
        # "is_setup_completed", 
        "created_method",
        "updated_method", 
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        # "deleted_at",
    )
    # 追加禁止
    def has_add_permission(self, request): return False
    # 削除禁止
    def has_delete_permission(self, request, obj=None):
        return False

# ------------------------------------------------------------------
# T_UserToken
# ------------------------------------------------------------------
@admin.register(T_UserToken)
class T_UserTokenAdmin(SaveAdminMixin, ModelAdmin):
    list_display = ("user", "token_type", "expired_at", "created_at", "deleted_at")
    list_filter = (SoftDeleteFilter, "token_type", "expired_at", "deleted_at")
    search_fields = ("user__email", "token_hash")
    readonly_fields = (
        "user",
        "token_type",
        "token_hash",
        # "expired_at",
        "created_method",
        "updated_method", 
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        # "deleted_at",
    )
    # 追加禁止
    def has_add_permission(self, request): return False
    # 削除禁止
    def has_delete_permission(self, request, obj=None):
        return False

# ------------------------------------------------------------------
# T_LoginHistory
# ------------------------------------------------------------------
@admin.register(T_LoginHistory)
class T_LoginHistoryAdmin(ModelAdmin): # 変更なし
    list_display = ("created_at", "login_identifier", "is_successful", "failure_reason", "ip_address", "deleted_at")
    list_filter = (SoftDeleteFilter, "is_successful", "failure_reason", "created_at")
    readonly_fields = ("user", "login_identifier", "is_successful", "failure_reason", "ip_address", "user_agent", "created_at", "updated_at")

    # 追加禁止
    def has_add_permission(self, request): return False
    # 編集禁止
    def has_change_permission(self, request, obj=None): return False
    # 削除禁止
    def has_delete_permission(self, request, obj=None):
        return False