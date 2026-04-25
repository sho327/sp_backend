import json
from datetime import datetime, date, time, timedelta
from django.contrib import admin
from django.urls import path
from django.utils import timezone
from django.views.generic import TemplateView
from unfold.views import UnfoldModelAdminViewMixin
from unfold.components import BaseComponent, register_component

from apps.account.admin import UserActivityView
from apps.artist.admin import ArtistSearchView
from apps.playlist.admin import TrackSearchView
from apps.artist.models import T_Artist
from apps.playlist.models import T_Playlist, T_PlaylistTrack
from core.utils.date_format import convert_to_site_timezone

# ------------------------------------------------------------------
# カスタムコンポーネント: 個人アクティビティ推移
# ------------------------------------------------------------------
@register_component
class PersonalActivityChart(BaseComponent):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        labels = []
        track_data = []
        artist_data = []
        # プロジェクト設定に基づいた現在の日付を取得
        today = convert_to_site_timezone(timezone.now()).date()
        
        # 過去7日間の各ユーザーの活動を集計
        for i in range(6, -1, -1):
            target_date = today - timedelta(days=i)
            labels.append(target_date.strftime("%m/%d"))
            
            # 日付の範囲をタイムゾーンを考慮して定義 (00:00:00 〜 23:59:59)
            # 共通関数 convert_to_site_timezone を通すことでプロジェクト設定(JST等)に合わせる
            start_datetime = convert_to_site_timezone(datetime.combine(target_date, time.min))
            end_datetime = convert_to_site_timezone(datetime.combine(target_date, time.max))
            
            # 楽曲登録数 (正確な時間範囲で集計)
            t_count = T_PlaylistTrack.objects.filter(
                playlist__user=user, 
                created_at__range=(start_datetime, end_datetime),
                deleted_at__isnull=True
            ).count()
            
            # アーティスト登録数 (正確な時間範囲で集計)
            a_count = T_Artist.objects.filter(
                created_by=user, 
                created_at__range=(start_datetime, end_datetime),
                deleted_at__isnull=True
            ).count()
            
            track_data.append(t_count)
            artist_data.append(a_count)

        context.update({
            "height": 240,
            "data": json.dumps({
                "labels": labels,
                "datasets": [
                    {
                        "type": "line",
                        "label": "登録楽曲数",
                        "data": track_data,
                        "borderColor": "#64748b",
                        "borderDash": [5, 5],
                        "borderWidth": 2,
                        "pointRadius": 4,
                        "pointBackgroundColor": "#64748b",
                        "backgroundColor": "transparent",
                        "tension": 0.3,
                        "order": 1
                    },
                    {
                        "type": "bar",
                        "label": "登録アーティスト数",
                        "data": artist_data,
                        "backgroundColor": "#3b82f6",
                        "borderRadius": 2,
                        "order": 2
                    }
                ]
            }),
            "options": json.dumps({
                "scales": {
                    "x": {"stacked": False},
                    "y": {"beginAtZero": True, "ticks": {"stepSize": 1}}
                },
                "plugins": {
                    "legend": {"display": True, "position": "bottom"},
                    "tooltip": {"mode": "index", "intersect": False}
                },
                "maintainAspectRatio": False
            })
        })
        return context

# ------------------------------------------------------------------
# ダッシュボードビュー (ホーム画面)
# ------------------------------------------------------------------
class DashboardView(UnfoldModelAdminViewMixin, TemplateView):
    title = "ホーム"
    permission_required = ()
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # 個人統計
        context.update({
            "my_artists_count": T_Artist.objects.filter(created_by=user, deleted_at__isnull=True).count(),
            "my_playlists_count": T_Playlist.objects.filter(user=user, deleted_at__isnull=True).count(),
            "my_tracks_count": T_PlaylistTrack.objects.filter(playlist__user=user, deleted_at__isnull=True).count(),
            "last_login": user.last_login,
        })
        
        # 最近の活動 (テーブルデータ)
        recent_tracks = T_PlaylistTrack.objects.filter(
            playlist__user=user, 
            deleted_at__isnull=True
        ).order_by("-created_at")[:5]
        
        rows = [
            [t.spotify_name, t.display_artist_name or t.spotify_artist_name, t.playlist.title, t.created_at.strftime("%Y/%m/%d %H:%M")]
            for t in recent_tracks
        ]

        context["table_data"] = {
            "headers": ["曲名", "アーティスト", "プレイリスト", "日時"],
            "rows": rows
        }

        # クイックアクセスリンク
        shortcuts = [
            {"title": "アーティスト検索", "icon": "person_search", "url": "artist_search", "color": "text-primary-600"},
            {"title": "トラック検索", "icon": "library_music", "url": "track_search", "color": "text-primary-600"},
        ]
        
        # 管理者のみ表示
        if user.is_superuser:
            shortcuts.extend([
                {"title": "アーティスト管理", "icon": "artist", "url": "artist_t_artist_changelist", "color": "text-slate-600"},
                {"title": "プレイリスト管理", "icon": "playlist_play", "url": "playlist_t_playlist_changelist", "color": "text-slate-600"},
            ])

        context["shortcuts"] = shortcuts
        
        return context

# ------------------------------------------------------------------
# カスタムページ/URL設定
# ------------------------------------------------------------------

# モデルに紐づかないサイト全体のカスタムページ用のダミーモデル
class DummyOpts:
    app_label = "admin"
    model_name = "custom_page"

# ダミーモデルの管理サイトクラス
class DummyModelAdmin:
    def __init__(self, admin_site):
        self.admin_site = admin_site
        self.opts = DummyOpts()

# カスタムURLをデフォルトの管理画面サイトに登録
_original_get_urls = admin.site.get_urls
def get_custom_admin_urls():
    # 元の管理画面のURLを取得
    urls = _original_get_urls()
    # ダミーモデルの管理サイトクラスのインスタンスを作成
    dummy_admin = DummyModelAdmin(admin.site)
    # カスタムURLのリスト
    custom_urls = [
        path("", admin.site.admin_view(DashboardView.as_view(model_admin=dummy_admin)), name="index"),
        path("user_activity/", admin.site.admin_view(UserActivityView.as_view(model_admin=dummy_admin)), name="user_activity"),
        path("artist_search/", admin.site.admin_view(ArtistSearchView.as_view(model_admin=dummy_admin)), name="artist_search"),
        path("track_search/", admin.site.admin_view(TrackSearchView.as_view(model_admin=dummy_admin)), name="track_search"),
    ]
    # カスタムURLを元の管理画面のURLに追加
    return custom_urls + urls

# 管理画面のURL取得関数を上書き
admin.site.get_urls = get_custom_admin_urls
