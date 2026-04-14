from django.contrib import admin
from django.utils.html import format_html

#  共通モジュール ---
from apps.common.models import T_SpotifyUserToken, T_FileResource

# ------------------------------------------------------------------
# T_SpotifyUserToken(Spotify認証トークン管理)
# ------------------------------------------------------------------
@admin.register(T_SpotifyUserToken)
class T_SpotifyUserTokenAdmin(admin.ModelAdmin):
    """
    SpotifyAPI接続用のトークン管理
    """
    list_display = ("id", "display_access_token", "expired_at", "display_status", "updated_at")
    readonly_fields = ("id", "created_at", "updated_at")
    
    fieldsets = (
        ("トークン情報", {
            "fields": ("id", "access_token", "refresh_token", "expired_at")
        }),
        ("リフレッシュ制御", {
            "fields": ("refreshing", "refreshing_until")
        }),
        ("システム情報", {
            "fields": ("created_method", "updated_method", "created_at", "updated_at", "deleted_at")
        }),
    )

    def display_access_token(self, obj):
        """トークンの冒頭のみを表示"""
        return f"{obj.access_token[:20]}..."
    display_access_token.short_description = "アクセストークン"

    def display_status(self, obj):
        """有効期限やロック状態をラベル表示"""
        if obj.is_refreshing():
            return format_html('<span style="color: #ff9800; font-weight: bold;">🔄 リフレッシュ中</span>')
        if obj.is_expired():
            return format_html('<span style="color: #f44336; font-weight: bold;">⚠️ 期限切れ</span>')
        return format_html('<span style="color: #4caf50; font-weight: bold;">✅ 有効</span>')
    display_status.short_description = "ステータス"

# ------------------------------------------------------------------
# T_FileResource (ファイルリソース管理)
# ------------------------------------------------------------------
@admin.register(T_FileResource)
class T_FileResourceAdmin(admin.ModelAdmin):
    """
    画像・外部URL等のファイルリソース管理
    """
    list_display = ("file_name", "file_type", "display_preview", "file_size_kb", "created_at")
    list_filter = ("file_type", "deleted_at")
    search_fields = ("file_name", "external_url")
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        ("基本情報", {
            "fields": ("id", "file_name", "file_type")
        }),
        ("リソース実体", {
            "fields": ("file_data", "external_url", "file_size")
        }),
        ("システム情報", {
            "fields": ("created_method", "updated_method", "created_at", "updated_at", "deleted_at")
        }),
    )

    def display_preview(self, obj):
        """管理画面上で画像のプレビューを表示"""
        if obj.url:
            return format_html('<img src="{}" style="width: 50px; height: auto; border-radius: 4px;" />', obj.url)
        return "-"
    display_preview.short_description = "プレビュー"

    def file_size_kb(self, obj):
        """バイト表記をKB表記に変換して表示"""
        if obj.file_size:
            return f"{round(obj.file_size / 1024, 2)} KB"
        return "-"
    file_size_kb.short_description = "サイズ"