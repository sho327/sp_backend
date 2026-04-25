# ------------------------------------------------------------------
# カスタムページ/URL設定
# ------------------------------------------------------------------
from django.contrib import admin
from django.urls import path
from apps.account.admin import UserActivityView
from apps.artist.admin import ArtistSearchView
from apps.playlist.admin import TrackSearchView

# モデルに紐づかないサイト全体のカスタムページ用のダミーモデル
class DummyOpts:
    app_label = "admin"
    model_name = "artist_search"

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
        path("user_activity/", admin.site.admin_view(UserActivityView.as_view(model_admin=dummy_admin)), name="user_activity"),
        path("artist_search/", admin.site.admin_view(ArtistSearchView.as_view(model_admin=dummy_admin)), name="artist_search"),
        path("track_search/", admin.site.admin_view(TrackSearchView.as_view(model_admin=dummy_admin)), name="track_search"),
    ]
    # カスタムURLを元の管理画面のURLに追加
    return custom_urls + urls

# 管理画面のURL取得関数を上書き
admin.site.get_urls = get_custom_admin_urls
