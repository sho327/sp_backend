import spotipy
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from typing import List
from urllib.parse import quote

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
    - ユーザー指定がある場合: ユーザー個別の権限で動作(T_SpotifyUserTokenを使用)
    - ユーザー指定がない場合: システム共通権限で動作(Client Credentials)
    """

    def __init__(self, email=None):
        self.email = email
        try:
            # クライアント生成時に認証(通信)が発生する可能性がある
            self.sp = self._get_client()
        except (SpotifyTokenNotFoundException, SpotifyAuthFailedException):
            # 認証関連やSpotify側のエラーはそのまま上に投げる(仕分け済みのため)
            raise
        # 2. Spotifyのサーバーダウンなど「外部サービス」エラー
        # _get_valid内で投げたもの、またはシステム認証時の通信エラー(500系)
        except (ExternalServiceError, SpotifyException) as e:
            # SpotifyException だった場合は、ここでExternalServiceErrorに変換して統一する
            if isinstance(e, SpotifyException):
                log_output_by_msg_id(
                    log_id="MSGE001",
                    params=[f"Spotify API initialization error: {str(e)}"],
                    logger_name=LOG_METHOD.APPLICATION.value,
                )
                raise ExternalServiceError() from e
            raise e

        # 3. その他、完全に予期せぬエラー
        except Exception as e:
            log_output_by_msg_id(
                log_id="MSGE001",
                params=[f"Unexpected error: {str(e)}"],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            raise ExternalServiceError() from e
            

    def _get_client(self):
        """認証モードに応じてSpotipyクライアントを初期化"""
        if self.email:
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

    def _get_valid_user_token(self) -> str:
        """
        DBから有効なアクセストークンを取得し、必要ならリフレッシュする
        排他制御(select_for_update)により並列リフレッシュを防ぐ
        """
        try:
            # 1. DBからトークン取得（select_for_updateでロック）
            token_obj: T_SpotifyUserToken = T_SpotifyUserToken.objects.select_for_update().get(
                email=self.email,
                deleted_at__isnull=True
            )
        except T_SpotifyUserToken.DoesNotExist:
            # DBにレコードがないのは「未連携」という認証状態の不備
            raise SpotifyTokenNotFoundException()

        # 2. リフレッシュが必要な場合の処理
        if token_obj.should_refresh():
            # 他のプロセスがリフレッシュ中かチェック
            if token_obj.is_refreshing():
                # ロックが解けるまで待機するか、エラーを投げる
                # 今回は簡易的にそのまま現在のトークンを返すが、本来は待機ロジックを推奨
                return token_obj.access_token
            
            # リフレッシュ中で無ければトークンリフレッシュを行う
            try:
                self._refresh_user_token(token_obj)
            except SpotifyException as e:
                # HTTP400は「リフレッシュトークンが無効(ユーザーが連携解除した等)」を指す
                if e.http_status in [400, 401]:
                    log_output_by_msg_id(
                        log_id="MSGE001",
                        params=[f"Spotify Auth Revoked: {str(e)}"],
                        logger_name=LOG_METHOD.APPLICATION.value,
                    )
                    raise SpotifyAuthFailedException() from e
                # それ以外の500系(Spotifyが落ちてる等)は外部サービスエラー
                raise ExternalServiceError() from e
            except Exception as e:
                # その他、DB保存失敗などはそのまま ApplicationError へ
                raise e

        return token_obj.access_token

    def _refresh_user_token(self, token_obj: T_SpotifyUserToken):
        """
        Spotify APIの /api/token エンドポイントへリフレッシュリクエストを送る
        エラー時はSpotifyExceptionがそのまま発生する。
        """
        # 1. ロック状態に更新
        token_obj.refreshing = True
        token_obj.refreshing_until = timezone.now() + timedelta(seconds=30)
        token_obj.save()

        try:
            # Spotipyのマネージャーを使用(内部でBasic認証ヘッダーを生成)
            # requestsで書く場合でも、このマネージャーがその責務を負う
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
            
            # 新しい refresh_token が発行された場合のみ上書き(ご提示のロジック通り)
            if 'refresh_token' in new_token_info:
                token_obj.refresh_token = new_token_info['refresh_token']
            
            # 有効期限の更新(expires_in秒後)
            token_obj.expired_at = timezone.now() + timedelta(seconds=new_token_info['expires_in'])
            
            # ロックの解除
            token_obj.refreshing = False
            token_obj.refreshing_until = None
            token_obj.save()

        except Exception as e:
            # 失敗時もロックを解除して保存(デッドロック防止)
            token_obj.refreshing = False
            token_obj.refreshing_until = None
            token_obj.save()
            # ここでは raise e する。特定のエラー判定は呼び出し側で行う。
            raise e
    
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
                raise ResourceNotFoundError() from e
            
            # それ以外の500系などは共通外部エラー
            log_output_by_msg_id(
                log_id="MSGE001",
                params=[f"Spotify API Error ({e.http_status}): {str(e)}"],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            raise ExternalServiceError() from e
        except Exception as e:
            # ネットワークエラー等
            log_output_by_msg_id(
                log_id="MSGE001",
                params=[f"Unexpected Network Error: {str(e)}"],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            raise ExternalServiceError() from e

    # ------------------------------------------------------------------
    # アーティスト関連/API実行メソッド(ラッパー経由で呼び出す)
    # ------------------------------------------------------------------
    # アーティスト情報取得(1件取得)
    def fetch_get_artist(self, spotify_id):
        return self._call_api(self.sp.artist, spotify_id)

    # アーティスト情報取得(一括取得)
    def fetch_get_artists(self, spotify_ids: list):
        if not spotify_ids:
            return []
        # spotipyのartists()は辞書を返すので、中身を取り出す
        results = self._call_api(self.sp.artists, spotify_ids)
        return results.get('artists', [])

    # 特定のアーティストに紐づく人気曲データ取得
    def fetch_get_artist_top_tracks(self, spotify_id, limit=5):
        results = self._call_api(self.sp.artist_top_tracks, spotify_id)
        return results.get("tracks", [])[:limit]
    
    # アーティスト検索
    def fetch_search_artists(self, query, limit=20):
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
    
    # ------------------------------------------------------------------
    # トラック関連/API実行メソッド(ラッパー経由で呼び出す)
    # ------------------------------------------------------------------
    # トラック(楽曲)情報取得 (1件取得)
    def fetch_get_track(self, spotify_id):
        """特定のトラック詳細を取得"""
        return self._call_api(self.sp.track, spotify_id)

    # トラック(楽曲)情報取得(一括取得)
    def fetch_get_tracks(self, spotify_ids: list):
        """複数のトラックを一括取得"""
        if not spotify_ids:
            return []
        results = self._call_api(self.sp.tracks, spotify_ids)
        return results.get('tracks', [])

    # トラック検索
    def fetch_search_tracks(self, query, limit=20):
        """キーワードによるトラック検索"""
        try:
            val = int(limit or 20)
            safe_limit = min(max(val, 1), 50)
        except (ValueError, TypeError):
            safe_limit = 20

        results = self._call_api(self.sp.search, q=query, limit=safe_limit, type='track')
        if results and 'tracks' in results:
            return results['tracks'].get('items', [])
        return []

    # レコメンデーション取得 (お勧め楽曲)
    def fetch_get_recommendations(
        self, seed_artists=None, seed_genres=None, seed_tracks=None, limit=20, **kwargs
    ):
        """
        指定されたシード(アーティスト、ジャンル、トラック)に基づきお勧め楽曲を取得
        ※seedは合計で最大5つまで指定可能
        """
        try:
            val = int(limit or 20)
            safe_limit = min(max(val, 1), 100)  # レコメンデーションは最大100まで可能
        except (ValueError, TypeError):
            safe_limit = 20

        results = self._call_api(
            self.sp.recommendations,
            seed_artists=seed_artists,
            seed_genres=seed_genres,
            seed_tracks=seed_tracks,
            limit=safe_limit,
            **kwargs,
        )
        return results.get("tracks", [])
    
    # ------------------------------------------------------------------
    # その他メソッド
    # ------------------------------------------------------------------
    def create_spotify_tracksets(
        track_ids: List[str], title: str = "MyList", chunk_size: int = 50
    ) -> List[str]:
        """
        入力:
        - track_ids: Spotify曲ID配列
        - title: URL上のタイトル文字列
        - chunk_size: 1URLあたりの最大曲数(デフォルト50)
        出力:
        - Trackset共有URL配列
        副作用:
        - なし（純粋関数）
        """
        urls = []
        encoded_title = quote(title)
        for i in range(0, len(track_ids), chunk_size):
            chunk = track_ids[i : i + chunk_size]
            ids = ",".join(chunk)
            urls.append(
                f"https://open.spotify.com/trackset/{encoded_title}_{i // chunk_size + 1}/{ids}"
            )
        return urls
