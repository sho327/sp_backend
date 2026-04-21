from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from simple_history.admin import SimpleHistoryAdmin

from apps.account.models import M_User, T_UserToken, T_LoginHistory, T_Profile

class SoftDeleteFilter(admin.SimpleListFilter):
    title = _('状態')
    parameter_name = 'is_deleted'

    def lookups(self, request, model_admin):
        return (
            ('active', _('有効のみ')),
            ('deleted', _('削除済みのみ')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(deleted_at__isnull=True)
        if self.value() == 'deleted':
            return queryset.filter(deleted_at__isnull=False)
        return queryset

# ------------------------------------------------------------------
# M_User (ユーザーマスタ)
# ------------------------------------------------------------------
@admin.register(M_User)
class M_UserAdmin(BaseUserAdmin, SimpleHistoryAdmin):
    """
    認証用ユーザーマスタの管理設定
    """
    # 一覧表示
    list_display = ("email", "is_active", "is_staff", "is_superuser", "last_login", "created_at", "deleted_at")
    list_filter = (SoftDeleteFilter, "is_active", "is_staff", "is_superuser", "deleted_at")
    ordering = ("-created_at",)

    # 編集画面のレイアウト
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("権限", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("重要日時", {"fields": ("last_login", "created_at", "updated_at", "deleted_at")}),
        ("システム情報", {"fields": ("created_method", "updated_method")}),
    )
    # 作成画面（パスワード設定が必要なため特別扱い）
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "is_active", "is_staff", "is_superuser"),
        }),
    )

    search_fields = ("email",)
    readonly_fields = ("id", "last_login", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        # 新規作成時 (change=False)
        if not change:
            # if not obj.updated_by:
            #     obj.updated_by = request.user
            # if not obj.updated_method:
            #     obj.updated_method = "admin_panel"
            
            # admin新規時は以下とする
            obj.created_by = request.user
            obj.created_method = "admin_panel"
            obj.updated_by = request.user
            obj.updated_method = "admin_panel"
        
        # 更新時(change=True)
        else:
            # 「更新時」は既存の値が入っているので、「手動でクリアされて空になった場合」や「意図的に上書きしたい場合」を考える必要がある
            # 基本的に「Adminで誰かが保存した」というログなら、強制的に上書きしても良いケースが多い？
            # ※「空の場合だけ自動セット」にしたいなら以下のようにする
            # if not obj.updated_by:
            #     obj.updated_by = request.user
            # if not obj.updated_method:
            #     obj.updated_method = "admin_panel"
            
            # admin更新時は以下とする
            obj.updated_by = request.user
            obj.updated_method = "admin_panel"
        
        super().save_model(request, obj, form, change)

# ------------------------------------------------------------------
# T_Profile (プロフィールトラン)
# ------------------------------------------------------------------
@admin.register(T_Profile)
class T_ProfileAdmin(SimpleHistoryAdmin):
    """
    ユーザープロフィールの管理設定
    """
    list_display = ("user_id_display", "display_name", "status_code", "is_setup_completed", "updated_at", "deleted_at")
    list_filter = (SoftDeleteFilter, "status_code", "is_setup_completed", "deleted_at")
    search_fields = ("user_id_display", "display_name", "user__email")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("user", "user_id_display", "display_name")}),
        ("詳細情報", {"fields": ("affiliation", "bio", "icon")}),
        ("状態・設定", {"fields": ("status_code", "is_setup_completed", "locked_until_at")}),
        ("システム情報", {"fields": ("created_method", "updated_method", "created_at", "updated_at", "deleted_at")}),
    )

    def save_model(self, request, obj, form, change):
        # 新規作成時 (change=False)
        if not change:
            # if not obj.updated_by:
            #     obj.updated_by = request.user
            # if not obj.updated_method:
            #     obj.updated_method = "admin_panel"
            
            # admin新規時は以下とする
            obj.created_by = request.user
            obj.created_method = "admin_panel"
            obj.updated_by = request.user
            obj.updated_method = "admin_panel"
        
        # 更新時(change=True)
        else:
            # 「更新時」は既存の値が入っているので、「手動でクリアされて空になった場合」や「意図的に上書きしたい場合」を考える必要がある
            # 基本的に「Adminで誰かが保存した」というログなら、強制的に上書きしても良いケースが多い？
            # ※「空の場合だけ自動セット」にしたいなら以下のようにする
            # if not obj.updated_by:
            #     obj.updated_by = request.user
            # if not obj.updated_method:
            #     obj.updated_method = "admin_panel"
            
            # admin更新時は以下とする
            obj.updated_by = request.user
            obj.updated_method = "admin_panel"
        
        super().save_model(request, obj, form, change)

# ------------------------------------------------------------------
# T_UserToken (ユーザ発行トークントラン)
# ------------------------------------------------------------------
@admin.register(T_UserToken)
class T_UserTokenAdmin(admin.ModelAdmin):
    """
    トークンの管理設定（履歴管理不要のためModelAdminを使用）
    """
    list_display = ("user", "token_type", "expired_at", "created_at", "deleted_at")
    list_filter = (SoftDeleteFilter, "token_type", "expired_at", "deleted_at")
    search_fields = ("user__email", "token_hash")
    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        # 新規作成時 (change=False)
        if not change:
            # if not obj.updated_by:
            #     obj.updated_by = request.user
            # if not obj.updated_method:
            #     obj.updated_method = "admin_panel"
            
            # admin新規時は以下とする
            obj.created_by = request.user
            obj.created_method = "admin_panel"
            obj.updated_by = request.user
            obj.updated_method = "admin_panel"
        
        # 更新時(change=True)
        else:
            # 「更新時」は既存の値が入っているので、「手動でクリアされて空になった場合」や「意図的に上書きしたい場合」を考える必要がある
            # 基本的に「Adminで誰かが保存した」というログなら、強制的に上書きしても良いケースが多い？
            # ※「空の場合だけ自動セット」にしたいなら以下のようにする
            # if not obj.updated_by:
            #     obj.updated_by = request.user
            # if not obj.updated_method:
            #     obj.updated_method = "admin_panel"
            
            # admin更新時は以下とする
            obj.updated_by = request.user
            obj.updated_method = "admin_panel"
        
        super().save_model(request, obj, form, change)

# ------------------------------------------------------------------
# T_LoginHistory (ログイン履歴)
# ------------------------------------------------------------------
@admin.register(T_LoginHistory)
class T_LoginHistoryAdmin(admin.ModelAdmin):
    """
    ログイン履歴の管理設定
    """
    list_display = ("created_at", "login_identifier", "is_successful", "failure_reason", "ip_address", "deleted_at")
    list_filter = (SoftDeleteFilter, "is_successful", "failure_reason", "created_at")
    search_fields = ("login_identifier", "ip_address", "user__email")
    readonly_fields = ("user", "login_identifier", "is_successful", "failure_reason",
                       "ip_address", "user_agent", "created_at", "updated_at")

    # 履歴は基本的に「見るだけ」にする
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
