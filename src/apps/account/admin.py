from django.contrib import admin
from datetime import datetime, date, time
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
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
    
    # def get_queryset(self, request):
    #     qs = super().get_queryset(request)
    #     if request.user.is_superuser:
    #         return qs
    #     # 一般スタッフは自分のみ表示
    #     return qs.filter(id=request.user.id)
    
    # def has_change_permission(self, request, obj=None):
    #     # スーパーユーザーは無条件でOK
    #     if request.user.is_superuser:
    #         return True
    #     # 対象のオブジェクトがある場合、その所有者が自分かチェック
    #     if obj is not None and obj.user != request.user:
    #         return False
    #     # 基本的な変更権限があるか確認
    #     return super().has_change_permission(request, obj)

    # def has_view_permission(self, request, obj=None):
    #     if request.user.is_superuser:
    #         return True
    #     if obj is not None and obj.user != request.user:
    #         return False
    #     return super().has_view_permission(request, obj)
    
    # 削除禁止
    def has_delete_permission(self, request, obj=None):
        return False
    
    # def save_model(self, request, obj, form, change):
    #     if not change:  # 新規作成時
    #         if not request.user.is_superuser:
    #             obj.user = request.user
    #     super().save_model(request, obj, form, change)

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
    # def get_queryset(self, request):
    #     qs = super().get_queryset(request)
    #     if request.user.is_superuser:
    #         return qs
    #     # 一般スタッフは自分が紐付いているデータのみ表示
    #     return qs.filter(user=request.user)
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



import json
from django.urls import path
from django.views.generic import TemplateView
from unfold.views import UnfoldModelAdminViewMixin
from django.db.models import Count
from apps.account.models import T_Profile, T_LoginHistory
from datetime import timedelta
from django.utils import timezone
from unfold.components import BaseComponent, register_component
from core.utils.date_format import convert_to_site_timezone
# ------------------------------------------------------------------
# カスタムページ(ユーザアクティビティ)
# ------------------------------------------------------------------
class UserActivityView(UnfoldModelAdminViewMixin, TemplateView):
    title = "ユーザアクティビティ"
    permission_required = ()
    template_name = "account/user_activity.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 1. ユーザステータスの集計
        status_counts = T_Profile.objects.values('status_code').annotate(count=Count('status_code'))
        stats = {item['status_code']: item['count'] for item in status_counts}
        
        # 2. 初期設定完了率の計算
        total = T_Profile.objects.count()
        completed = T_Profile.objects.filter(is_setup_completed=True).count()
        percent = int((completed / total * 100)) if total > 0 else 0

        # 3. ログイン失敗ログの整形
        failures = T_LoginHistory.objects.filter(is_successful=False).order_by('-created_at')[:10]
        rows = [
            [log.login_identifier, str(log.get_failure_reason_display()), log.created_at.strftime("%Y/%m/%d %H:%M")]
            for log in failures
        ]

        # 4. コンテキスト更新
        context.update({
            "active_users": stats.get(10, 0),
            "locked_users": stats.get(30, 0),
            "frozen_users": stats.get(40, 0),
            "withdrawn_users": stats.get(99, 0),
            
            # プログレスバー用データ
            "setup_completion_percent": percent,
            
            # テーブル用データ
            "table_data": {
                "headers": ["ユーザ識別子", "失敗理由", "日時"],
                "rows": rows
            }
        })
        
        return context

# ログイン試行履歴/コンポーネント
@register_component
class LoginTrendChart(BaseComponent):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        labels = []
        total_data = []
        success_data = []
        failure_data = []
        # プロジェクト設定に基づいた現在の日付を取得
        today = convert_to_site_timezone(timezone.now()).date()
        
        # 過去7日分のデータを集計
        for i in range(6, -1, -1):
            target_date = today - timedelta(days=i)
            labels.append(target_date.strftime("%m/%d"))

            # 日付の範囲をタイムゾーンを考慮して定義 (00:00:00 〜 23:59:59)
            # 共通関数 convert_to_site_timezone を通すことでプロジェクト設定(JST等)に合わせる
            start_datetime = convert_to_site_timezone(datetime.combine(target_date, time.min))
            end_datetime = convert_to_site_timezone(datetime.combine(target_date, time.max))

            # データベースから対象日の全ログインログを正確な時間範囲で抽出
            day_queryset = T_LoginHistory.objects.filter(created_at__range=(start_datetime, end_datetime))
            
            # 成功/失敗をそれぞれカウント
            success_count = day_queryset.filter(is_successful=True).count()
            failure_count = day_queryset.filter(is_successful=False).count()
            
            success_data.append(success_count)
            failure_data.append(failure_count)
            # 成功＋失敗の合計値を計算（折れ線用）
            total_data.append(success_count + failure_count)

        context.update({
            "height": 240,
            "data": json.dumps({
                "labels": labels,
                "datasets": [
                    # --- 【データセット1】合計試行数 (点線の折れ線) ---
                    {
                        "type": "line",                # 混合グラフにするため明示的にlineを指定
                        "label": "合計試行数",
                        "data": total_data,
                        "borderColor": "#64748b",      # Slate 500: 目立ちすぎない落ち着いたグレー
                        "borderDash": [5, 5],          # 点線の設定: 5px描画して5px空ける
                        "borderWidth": 2,              # 線の太さ
                        "pointRadius": 4,              # プロット点のサイズ（クリックやホバーをしやすくする）
                        "pointBackgroundColor": "#64748b",
                        "backgroundColor": "transparent", # 線の下を塗りつぶさない
                        "tension": 0.3,                # 0.4より少し抑えて、データの変化をシャープに見せる
                        "order": 1                     # 描画の重なり順: 1にすることで棒グラフの手前に表示
                    },
                    # --- 【データセット2】成功数 (緑の棒) ---
                    {
                        "type": "bar",
                        "label": "成功",
                        "data": success_data,
                        "backgroundColor": "#10b981",  # Emerald 500: ポジティブな緑
                        "borderRadius": 2,             # 棒の角をわずかに丸くする（モダンな印象に）
                        "order": 2                     # 折れ線の後ろ側に描画
                    },
                    # --- 【データセット3】失敗数 (赤の棒) ---
                    {
                        "type": "bar",
                        "label": "失敗",
                        "data": failure_data,
                        "backgroundColor": "#ef4444",  # Red 500: 警告を意味する赤
                        "borderRadius": 2,             # 角丸
                        "order": 2                     # 折れ線の後ろ側に描画
                    }
                ]
            }),
            "options": json.dumps({
                "scales": {
                    "x": {
                        # stacked: False により、成功と失敗を「積み上げ」ず「並列」にする
                        # 失敗が成功の下に隠れるのを防ぎ、赤い棒を常に見えるようにする
                        "stacked": False,
                    },
                    "y": {
                        "beginAtZero": True,           # 最小値を必ず0にする
                        "ticks": {"stepSize": 1}       # 1件刻みの整数でメモリを表示
                    }
                },
                "plugins": {
                    "legend": {
                        "display": True,               # 各色のラベル（凡例）を表示
                        "position": "bottom"           # グラフの下側に配置
                    },
                    "tooltip": {
                        # マウスを合わせた時、同じ日付(index)のデータをまとめてツールチップに出す
                        "mode": "index",
                        "intersect": False             # 線や棒にピッタリ合わせなくても表示されるようにする
                    }
                },
                "maintainAspectRatio": False          # 親要素の高さ(height: 240)に合わせて伸縮させる
            })
        })
        return context