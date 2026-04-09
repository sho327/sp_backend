from datetime import timedelta

import spotipy
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

# --- 共通モジュール ---
from apps.common.models import T_SpotifyUserToken

# --- コアモジュール ---
from core.consts import LOG_METHOD
from core.exceptions.exceptions import ExternalServiceError
from core.utils.log_helpers import log_output_by_msg_id


class SpotifyService:
    """
    Spotify APIサービス
    - ユーザー指定がある場合: ユーザー個別の権限で動作 (T_SpotifyUserTokenを使用)
    - ユーザー指定がない場合: システム共通権限で動作 (Client Credentials)
    """

    def __init__(self, user=None):
        self.user = user
        self.sp = self._get_client()

    def _get_client(self):
        """認証モードに応じてSpotipyクライアントを初期化"""
        if self.user:
            # ユーザー認証モード
            token = self._get_valid_user_token()
            return spotipy.Spotify(auth=token)
        else:
            # システム認証モード
            auth_manager = SpotifyClientCredentials(
                client_id=settings.SPOTIFY_CLIENT_ID,
                client_secret=settings.SPOTIFY_CLIENT_SECRET,
            )
            return spotipy.Spotify(auth_manager=auth_manager)

    @transaction.atomic
    def _get_valid_user_token(self) -> str:
        """
        DBから有効なアクセストークンを取得し、必要ならリフレッシュする
        排他制御(select_for_update)により並列リフレッシュを防ぐ
        """
        try:
            # DBからトークン情報を取得(行ロック)
            token_obj = T_SpotifyUserToken.objects.select_for_update().get(
                user=self.user,  # もしモデルにuser紐付けがある場合
                deleted_at__isnull=True,
            )
        except T_SpotifyUserToken.DoesNotExist:
            raise ExternalServiceError("Spotify連携設定が見つかりません。")

        # リフレッシュが必要か判定 (期限切れ 5分前)
        if token_obj.should_refresh():
            # 他のプロセスがリフレッシュ中かチェック
            if token_obj.is_refreshing():
                # ロックが解けるまで待機するか、エラーを投げる
                # 今回は簡易的にそのまま現在のトークンを返すが、本来は待機ロジックを推奨
                return token_obj.access_token

            # リフレッシュ実行
            self._refresh_user_token(token_obj)

        return token_obj.access_token

    def _refresh_user_token(self, token_obj):
        """
        Spotify APIの /api/token エンドポイントへリフレッシュリクエストを送る
        """
        # 1. ロック状態に更新
        token_obj.refreshing = True
        token_obj.refreshing_until = timezone.now() + timedelta(seconds=30)
        token_obj.save()

        try:
            # Spotipyのマネージャーを使用（内部で Basic 認証ヘッダーを生成してくれる）
            # もし requests で書く場合でも、このマネージャーがその責務を負います
            oauth = SpotifyOAuth(
                client_id=settings.SPOTIFY_CLIENT_ID,
                client_secret=settings.SPOTIFY_CLIENT_SECRET,
                redirect_uri=settings.SPOTIFY_REDIRECT_URI,
            )

            # リフレッシュ実行 (内部で Basic 認証 + refresh_token 送信)
            # data = {"grant_type": "refresh_token", "refresh_token": ...}
            new_token_info = oauth.refresh_access_token(token_obj.refresh_token)

            # 2. データの更新
            token_obj.access_token = new_token_info["access_token"]

            # 新しい refresh_token が発行された場合のみ上書き（ご提示のロジック通り）
            if "refresh_token" in new_token_info:
                token_obj.refresh_token = new_token_info["refresh_token"]

            # 有効期限の更新 (expires_in 秒後)
            token_obj.expired_at = timezone.now() + timedelta(
                seconds=new_token_info["expires_in"]
            )

            # ロック解除
            token_obj.refreshing = False
            token_obj.refreshing_until = None
            token_obj.save()

        except Exception as e:
            # 失敗時もロックを解除して保存（デッドロック防止）
            token_obj.refreshing = False
            token_obj.refreshing_until = None
            token_obj.save()
            log_output_by_msg_id(
                log_id="MSGE001",
                params=[f"Spotify token refresh failed: {str(e)}"],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            raise ExternalServiceError("Spotifyの認証更新に失敗しました。") from e

    # ------------------------------------------------------------------
    # API 実行メソッド (spクライアントを使用)
    # ------------------------------------------------------------------
    def fetch_artist_detail(self, spotify_id):
        """アーティスト詳細取得"""
        try:
            return self.sp.artist(spotify_id)
        except Exception as e:
            raise ExternalServiceError() from e

    def fetch_artists_batch(self, spotify_ids: list):
        """最大50件のIDを一括で受け取り、詳細情報のリストを返す"""
        if not spotify_ids:
            return []
        try:
            results = self.sp.artists(spotify_ids)
            return results["artists"]
        except Exception as e:
            raise ExternalServiceError() from e

    def fetch_top_tracks(self, spotify_id, limit=5):
        """指定したアーティストの人気曲を取得（プレイリスト生成用）"""
        try:
            results = self.sp.artist_top_tracks(spotify_id)
            return [track["uri"] for track in results["tracks"][:limit]]
        except Exception as e:
            raise ExternalServiceError() from e

    def search_track_uri(self, artist_name: str, track_name: str):
        """アーティスト名と曲名でSpotifyトラックを検索し、先頭1件のURIを返す。"""
        try:
            query = f"artist:{artist_name} track:{track_name}"
            results = self.sp.search(q=query, type="track", limit=1)
            items = results.get("tracks", {}).get("items", [])
            if not items:
                return None
            return items[0]["uri"]
        except Exception as e:
            raise ExternalServiceError() from e

    def fetch_recommendation_tracks(
        self, seed_artists, target_valence=0.5, target_energy=0.5, limit=20
    ):
        """ムード条件とシードアーティストに基づく推薦曲URIを返す。"""
        try:
            if not seed_artists:
                return []
            safe_limit = max(1, min(int(limit), 100))
            results = self.sp.recommendations(
                seed_artists=seed_artists[:5],
                limit=safe_limit,
                target_valence=float(target_valence),
                target_energy=float(target_energy),
            )
            return [track["uri"] for track in results.get("tracks", [])]
        except Exception as e:
            raise ExternalServiceError() from e

    def fetch_tracks_detail_by_uris(self, uris):
        """URI配列からトラック詳細をまとめて取得する。"""
        if not uris:
            return []
        try:
            tracks = self.sp.tracks(uris).get("tracks", [])
            formatted = []
            for track in tracks:
                if not track:
                    continue
                formatted.append(
                    {
                        "uri": track.get("uri"),
                        "name": track.get("name"),
                        "artists": [a.get("name") for a in track.get("artists", [])],
                        "spotify_id": track.get("id"),
                        "preview_url": track.get("preview_url"),
                        "external_url": track.get("external_urls", {}).get("spotify"),
                    }
                )
            return formatted
        except Exception as e:
            raise ExternalServiceError() from e

    def search_tracks(self, q: str, artist_spotify_id: str = None, limit: int = 20):
        """トラック検索（任意でアーティスト絞り込み）。"""
        try:
            safe_limit = max(1, min(int(limit), 50))
            query = q.strip()
            if artist_spotify_id:
                query = f"{query} artist:{artist_spotify_id}"

            results = self.sp.search(q=query, limit=safe_limit, type="track")
            items = results.get("tracks", {}).get("items", [])
            return [
                {
                    "spotify_id": item.get("id"),
                    "uri": item.get("uri"),
                    "name": item.get("name"),
                    "artists": [a.get("name") for a in item.get("artists", [])],
                    "preview_url": item.get("preview_url"),
                    "external_url": item.get("external_urls", {}).get("spotify"),
                }
                for item in items
            ]
        except Exception as e:
            raise ExternalServiceError() from e

    def search_artists(self, query, limit=20):
        """アーティスト検索"""
        try:
            # 数値バリデーション
            try:
                val = int(limit)
            except (TypeError, ValueError):
                val = 20
            safe_limit = min(max(val, 1), 50)

            results = self.sp.search(q=query, limit=safe_limit, type="artist")

            if results and "artists" in results:
                return results["artists"].get("items", [])
            return []
        except Exception as e:
            raise ExternalServiceError() from e


# -----------------------------------------
# # 実行例
# -----------------------------------------
# システム権限（検索など）
# service = SpotifyService()
# ユーザー権限（ユーザー操作など）
# service = SpotifyService(user=user_profile)
# -----------------------------------------
