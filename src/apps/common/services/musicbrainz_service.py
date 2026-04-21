import requests
from django.core.cache import cache

# --- コアモジュール ---
from core.consts import LOG_METHOD
from core.utils.log_helpers import log_output_by_msg_id
from core.exceptions.exceptions import ExternalServiceError

# --- 共通モジュール ---
from apps.common.exceptions import ArtistMBIDNotFoundError

class MusicBrainzService:
    """
    MusicBrainz API サービス (全機能集約・共通化版)
    """
    BASE_URL = "https://musicbrainz.org/ws/2"

    def __init__(self):
        self.headers = {
            "User-Agent": "SetlistSync/1.0.0 ( shogo@example.com )",
            "Accept": "application/json"
        }

    def _call_api(self, endpoint: str, params: dict = None) -> dict:
        """
        API実行・エラーハンドリング・ログ出力の共通ラッパー
        not_found_exc: 404発生時に投げたいカスタム例外を指定可能
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        # デバッグログ
        log_output_by_msg_id(
            log_id="MSGD001",
            params=[f"MusicBrainzAPI/DEBUG: Calling {url} with {params}"],
            logger_name=LOG_METHOD.APPLICATION.value,
        )

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=7)

            # 404エラーハンドリング
            if response.status_code == 404:
                log_output_by_msg_id(
                    log_id="MSGW001",
                    params=[f"MusicBrainzAPI Target URL is Not Found Error: {url}"],
                    logger_name=LOG_METHOD.APPLICATION.value,
                )
                raise ExternalServiceError()

            # 500系エラーハンドリング
            if response.status_code >= 500:
                log_output_by_msg_id(
                    log_id="MSGW001",
                    params=[f"MusicBrainz Server Error: {response.status_code}"],
                    logger_name=LOG_METHOD.APPLICATION.value,
                )
                raise ExternalServiceError()

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            log_output_by_msg_id(
                log_id="MSGW001",
                params=[f"MusicBrainz Timeout: {url}"],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            raise ExternalServiceError()
        except requests.exceptions.RequestException as e:
            log_output_by_msg_id(
                log_id="MSGW001",
                params=[f"MusicBrainz Connection Error: {str(e)}"],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            raise ExternalServiceError()

    # ------------------------------------------------------------------
    # fetchメソッド群 (API通信)
    # ------------------------------------------------------------------
    def fetch_url(self, resource_url: str) -> dict:
        """Spotify URL等からMBID情報を取得"""
        params = {"resource": resource_url, "inc": "artist-rels", "fmt": "json"}
        return self._call_api("/url", params=params)

    # ------------------------------------------------------------------
    # ビジネスロジック
    # ------------------------------------------------------------------
    def get_artist_by_spotify_id(self, spotify_id: str) -> dict:
        """Spotify IDから取得"""
        url = f"https://open.spotify.com/artist/{spotify_id}"
        return self._get_artist_by_resource_url(url, f"spotify_{spotify_id}")

    def get_artist_by_deezer_id(self, deezer_id: str) -> dict:
        """Deezer IDから取得"""
        # DeezerのURL形式: https://www.deezer.com/artist/{deezer_id}
        url = f"https://www.deezer.com/artist/{deezer_id}"
        return self._get_artist_by_resource_url(url, f"deezer_{deezer_id}")

    def _get_artist_by_resource_url(self, resource_url: str, cache_identifier: str) -> dict:
        """
        ソースURL(Spotify/Deezer等)からMBIDを取得する内部共通メソッド
        """
        cache_key = f"mb_lookup_{cache_identifier}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
        
        # ここでfetch_urlを呼び出す。404等の例外ハンドリングは_call_apiに集約済み
        data = self.fetch_url(resource_url)

        # 抽出ロジック
        relations = data.get("relations", [])
        for rel in relations:
            if rel.get("target-type") == "artist":
                artist_data = rel.get("artist", {})
                result = {
                    "mbid": artist_data.get("id"),
                    "name": artist_data.get("name"),
                    "sort_name": artist_data.get("sort-name")
                }
                cache.set(cache_key, result, 60 * 60 * 24)
                return result
        
        # データが見つからなかった場合の警告ログと例外
        log_output_by_msg_id(
            log_id="MSGW001",
            params=[f"MusicBrainz ID is Not Found Error for URL={resource_url}"],
            logger_name=LOG_METHOD.APPLICATION.value,
        )
        raise ArtistMBIDNotFoundError()