import spotipy
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from datetime import timedelta

# --- コアモジュール ---
from core.consts import LOG_METHOD
from core.utils.log_helpers import log_output_by_msg_id
from core.exceptions.exceptions import (
    ExternalServiceError,
    ResourceNotFoundError,
)

# --- 共通モジュール ---
from apps.common.models import T_SpotifyUserToken
from apps.common.exceptions import (
    SpotifyTokenNotFoundException,
    SpotifyAuthFailedException,
    SpotifyApiLimitException
)

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
                client_secret=settings.SPOTIFY_CLIENT_SECRET
            )
            return spotipy.Spotify(auth_manager=auth_manager)

    @transaction.atomic
    def _get_valid_user_token(self) -> str:
        """
        DBから有効なアクセストークンを取得し、必要ならリフレッシュする
        排他制御(select_for_update)により並列リフレッシュを防ぐ
        """
        try:
            # 1. DBからトークン取得（select_for_updateでロック）
            token_obj: T_SpotifyUserToken = T_SpotifyUserToken.objects.select_for_update().get(
                user=self.user.email,
                deleted_at__isnull=True
            )
        except T_SpotifyUserToken.DoesNotExist:
            # 専用の404系エラーを投げる
            raise SpotifyTokenNotFoundException()

        # 2. リフレッシュが必要な場合の処理
        if token_obj.should_refresh():
            # 他のプロセスがリフレッシュ中かチェック
            if token_obj.is_refreshing():
                # ロックが解けるまで待機するか、エラーを投げる
                # 今回は簡易的にそのまま現在のトークンを返すが、本来は待機ロジックを推奨
                return token_obj.access_token
            
            try:
                self._refresh_user_token(token_obj)
            except Exception as e:
                # リフレッシュ失敗は外部サービスエラーとして記録
                log_output_by_msg_id("MSGE001", [f"Token refresh failed: {str(e)}"])
                raise ExternalServiceError("認証情報の更新に失敗しました。") from e

        return token_obj.access_token

    def _refresh_user_token(self, token_obj: T_SpotifyUserToken):
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
                redirect_uri=settings.SPOTIFY_REDIRECT_URI
            )
            
            # リフレッシュ実行 (内部で Basic 認証 + refresh_token 送信)
            # data = {"grant_type": "refresh_token", "refresh_token": ...}
            new_token_info = oauth.refresh_access_token(token_obj.refresh_token)
            
            # 2. データの更新
            token_obj.access_token = new_token_info['access_token']
            
            # 新しい refresh_token が発行された場合のみ上書き（ご提示のロジック通り）
            if 'refresh_token' in new_token_info:
                token_obj.refresh_token = new_token_info['refresh_token']
            
            # 有効期限の更新 (expires_in 秒後)
            token_obj.expired_at = timezone.now() + timedelta(seconds=new_token_info['expires_in'])
            
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
                logger_name=LOG_METHOD.APPLICATION.value
            )
            raise ExternalServiceError("Spotifyの認証更新に失敗しました。") from e
    
    def _call_api(self, func, *args, **kwargs):
        """
        Spotify API実行用の共通ラッパー。
        API特有のエラーを解析し、定義したExceptionへ変換する。
        """
        try:
            return func(*args, **kwargs)
        except SpotifyException as e:
            # statusコードに基づいて分類
            if e.http_status == 401:
                raise SpotifyAuthFailedException() from e
            if e.http_status == 429:
                raise SpotifyApiLimitException() from e
            if e.http_status == 404:
                raise ResourceNotFoundError("Spotify上にリソースが見つかりません。") from e
            
            # それ以外の500系などは共通外部エラー
            log_output_by_msg_id("MSGE001", [f"Spotify API Error ({e.http_status}): {str(e)}"])
            raise ExternalServiceError() from e
        except Exception as e:
            # ネットワークエラーなど
            log_output_by_msg_id("MSGE001", [f"Unexpected Network Error: {str(e)}"])
            raise ExternalServiceError() from e

    # ------------------------------------------------------------------
    # API 実行メソッド (ラッパー経由で呼び出す)
    # ------------------------------------------------------------------
    def fetch_artist_detail(self, spotify_id):
        return self._call_api(self.sp.artist, spotify_id)

    def fetch_artists_batch(self, spotify_ids: list):
        if not spotify_ids:
            return []
        # spotipyのartists()は辞書を返すので、中身を取り出す
        results = self._call_api(self.sp.artists, spotify_ids)
        return results.get('artists', [])

    def fetch_top_tracks(self, spotify_id, limit=5):
        results = self._call_api(self.sp.artist_top_tracks, spotify_id)
        return [track['uri'] for track in results.get('tracks', [])[:limit]]

    def search_artists(self, query, limit=20):
        # APIを叩く前の事前バリデーション
        try:
            val = int(limit or 20)
            safe_limit = min(max(val, 1), 50)
        except (ValueError, TypeError):
            safe_limit = 20

        results = self._call_api(self.sp.search, q=query, limit=safe_limit, type='artist')
        if results and 'artists' in results:
            return results['artists'].get('items', [])
        return []


# -----------------------------------------
# # 実行例
# -----------------------------------------
# システム権限（検索など）
# service = SpotifyService()
# ユーザー権限（ユーザー操作など）
# service = SpotifyService(user=user_profile)
# -----------------------------------------
