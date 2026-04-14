# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# from simple_history.admin import SimpleHistoryAdmin

# from apps.account.models import M_User, T_UserToken, T_LoginHistory, T_Profile

# # ------------------------------------------------------------------
# # M_User (ユーザーマスタ)
# # ------------------------------------------------------------------
# @admin.register(M_User)
# class M_UserAdmin(BaseUserAdmin, SimpleHistoryAdmin):
#     """
#     認証用ユーザーマスタの管理設定
#     """
#     # 一覧表示
#     list_display = ("email", "is_active", "is_staff", "is_superuser", "last_login", "created_at")
#     list_filter = ("is_active", "is_staff", "is_superuser", "deleted_at")
#     ordering = ("-created_at",)

#     # 編集画面のレイアウト
#     fieldsets = (
#         (None, {"fields": ("email", "password")}),
#         ("権限", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
#         ("重要日時", {"fields": ("last_login", "created_at", "updated_at", "deleted_at")}),
#         ("システム情報", {"fields": ("created_method", "updated_method")}),
#     )
#     # 作成画面（パスワード設定が必要なため特別扱い）
#     add_fieldsets = (
#         (None, {
#             "classes": ("wide",),
#             "fields": ("email", "is_active", "is_staff", "is_superuser"),
#         }),
#     )

#     search_fields = ("email",)
#     readonly_fields = ("id", "last_login", "created_at", "updated_at")

# # ------------------------------------------------------------------
# # T_Profile (プロフィールトラン)
# # ------------------------------------------------------------------
# @admin.register(T_Profile)
# class T_ProfileAdmin(SimpleHistoryAdmin):
#     """
#     ユーザープロフィールの管理設定
#     """
#     list_display = ("user_id_display", "display_name", "status_code", "is_setup_completed", "updated_at")
#     list_filter = ("status_code", "is_setup_completed", "deleted_at")
#     search_fields = ("user_id_display", "display_name", "user__email")
#     readonly_fields = ("created_at", "updated_at")

#     fieldsets = (
#         (None, {"fields": ("user", "user_id_display", "display_name")}),
#         ("詳細情報", {"fields": ("affiliation", "bio", "icon")}),
#         ("状態・設定", {"fields": ("status_code", "is_setup_completed", "locked_until_at")}),
#         ("システム情報", {"fields": ("created_method", "updated_method", "created_at", "updated_at", "deleted_at")}),
#     )

# # ------------------------------------------------------------------
# # T_UserToken (ユーザ発行トークントラン)
# # ------------------------------------------------------------------
# @admin.register(T_UserToken)
# class T_UserTokenAdmin(admin.ModelAdmin):
#     """
#     トークンの管理設定（履歴管理不要のためModelAdminを使用）
#     """
#     list_display = ("user", "token_type", "expired_at", "created_at")
#     list_filter = ("token_type", "expired_at", "deleted_at")
#     search_fields = ("user__email", "token_hash")
#     readonly_fields = ("created_at", "updated_at")

# # ------------------------------------------------------------------
# # T_LoginHistory (ログイン履歴)
# # ------------------------------------------------------------------
# @admin.register(T_LoginHistory)
# class T_LoginHistoryAdmin(admin.ModelAdmin):
#     """
#     ログイン履歴の管理設定
#     """
#     list_display = ("created_at", "login_identifier", "is_successful", "failure_reason", "ip_address")
#     list_filter = ("is_successful", "failure_reason", "created_at")
#     search_fields = ("login_identifier", "ip_address", "user__email")
#     readonly_fields = ("user", "login_identifier", "is_successful", "failure_reason",
#                        "ip_address", "user_agent", "created_at", "updated_at")

#     # 履歴は基本的に「見るだけ」にする
#     def has_add_permission(self, request):
#         return False

#     def has_change_permission(self, request, obj=None):
#         return False
