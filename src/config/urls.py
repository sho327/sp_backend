from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from apps.account.urls import router as account_router
from apps.artist.urls import router as artist_router

BASE_API_PATH = "api/v1"

urlpatterns = [
    # 管理者機能
    path("admin/", admin.site.urls),
    # アカウント機能
    path(f"{BASE_API_PATH}/account/", include(account_router.urls)),
    path(f"{BASE_API_PATH}/account/", include("apps.account.urls")),
    # アーティスト機能
    path(f"{BASE_API_PATH}/artist/", include(artist_router.urls)),
    path(f"{BASE_API_PATH}/artist/", include("apps.artist.urls")),
    # プレイリスト機能
    path(f"{BASE_API_PATH}/playlist/", include("apps.playlist.urls")),

# 静的ファイル配信
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
