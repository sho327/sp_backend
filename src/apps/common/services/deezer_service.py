import requests
from typing import List

# --- コアモジュール ---
from core.consts import LOG_METHOD
from core.utils.log_helpers import log_output_by_msg_id
from core.exceptions.exceptions import (
    ExternalServiceError,
    ResourceNotFoundError,
)

# --- 共通モジュール ---
from apps.common.exceptions import (
    DeezerAuthFailedException,
    DeezerApiLimitException,
    DeezerPermissionDeniedException
)

class DeezerService:
    """
    DeezerAPI サービス
    - 公式SDKがないため、requestsを用いて直接APIを叩く構成
    """
    BASE_URL = "https://api.deezer.com"

    def _call_api(self, endpoint: str, params: dict = None):
        url = f"{self.BASE_URL}{endpoint}"

        # デバッグログ出力
        log_output_by_msg_id(
            log_id="MSGD001",
            params=[f"DeezerAPI/DEBUG: Calling {url} with {params}"],
            logger_name=LOG_METHOD.APPLICATION.value,
        )
        try:
            response = requests.get(url, params=params, timeout=10)
            
            # APIエラー発生時、レスポンス内の情報を確認
            if response.status_code != 200:
                # 404の場合は共通のResourceNotFoundErrorを使う（なければ定義してください）
                if response.status_code == 404:
                    # 警告ログ出力
                    log_output_by_msg_id(
                        log_id="MSGW001",
                        params=[f"DeezerAPI Not Found Error. url :{url} params: {str(params)}"],
                        logger_name=LOG_METHOD.APPLICATION.value,
                    )
                    raise ResourceNotFoundError()
                
                # 403 Forbidden
                if response.status_code == 403:
                    # 警告ログ出力
                    log_output_by_msg_id(
                        log_id="MSGW001",
                        params=[f"DeezerAPI permission Error: {response.status_code}"],
                        logger_name=LOG_METHOD.APPLICATION.value,
                    )
                    raise DeezerPermissionDeniedException()
                    
                # 429 Too Many Requests
                if response.status_code == 429:
                    # 警告ログ出力
                    log_output_by_msg_id(
                        log_id="MSGW001",
                        params=[f"DeezerAPI Late Limit Error."],
                        logger_name=LOG_METHOD.APPLICATION.value,
                    )
                    raise DeezerApiLimitException()

                # その他のエラーはExternalServiceError
                # 警告ログ出力
                log_output_by_msg_id(
                    log_id="MSGW001",
                    params=[f"DeezerAPI Error."],
                    logger_name=LOG_METHOD.APPLICATION.value,
                )
                raise ExternalServiceError()

            response.raise_for_status()
            data = response.json()
            # デバッグログ出力
            log_output_by_msg_id(
                log_id="MSGD001",
                params=[f"DeezerAPI/DEBUG: Calling {url} Response.json {data}"],
                logger_name=LOG_METHOD.APPLICATION.value,
            )

            # Deezer特有のレスポンス内エラーチェック
            if "error" in data:
                error_type = data["error"].get("type")
                if error_type == "OAuthException":
                    log_output_by_msg_id(
                        log_id="MSGW001",
                        params=[f"Deezer API Auth Error: {data["error"].get("message")}"],
                        logger_name=LOG_METHOD.APPLICATION.value,
                    )
                    raise DeezerAuthFailedException()
                
                log_output_by_msg_id(
                    log_id="MSGW001",
                    params=[f"Deezer Error: {data["error"].get("message")}"],
                    logger_name=LOG_METHOD.APPLICATION.value,
                )
                raise ExternalServiceError(data["error"].get("message"))

            return data

        except requests.exceptions.RequestException as e:
            # 通信そのものが失敗した場合
            log_output_by_msg_id(
                log_id="MSGW001",
                params=[f"Deezer Network Error: {str(e)}"],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            raise ExternalServiceError() from e

    # ------------------------------------------------------------------
    # アーティスト関連
    # ------------------------------------------------------------------
    # アーティスト情報取得(1件取得)
    def fetch_get_artist(self, artist_id: str) -> dict:
        return self._call_api(f"/artist/{artist_id}")

    # アーティスト情報取得(一括取得)
    def fetch_get_artists(self, artist_ids: List[str]) -> List[dict]:
        if not artist_ids:
            return []
        # Deezerには一括取得がないため、個別リクエストをループする
        return [self.fetch_get_artist(aid) for aid in artist_ids]
    
    # アーティスト検索
    def fetch_search_artists(self, query: str, limit: int = 10) -> list:
        params = {"q": query, "limit": limit}
        data = self._call_api("/search/artist", params=params)
        return data.get("data", [])

    # ------------------------------------------------------------------
    # トラック関連
    # ------------------------------------------------------------------
    # 2026/04/19 SpotifyAPIは規約が厳しいので、deezerへ移行する準備だけ整えておく
    # トラック情報取得(1件取得)
    def fetch_get_track(self, track_id: str) -> dict:
        return self._call_api(f"/track/{track_id}")

    # # トラック情報取得(一括取得)
    # def fetch_get_tracks(self, track_ids: List[str]) -> List[dict]:
    #     if not track_ids:
    #         return []
    #     # Deezerには一括取得がないため、個別リクエストをループする
    #     return [self.fetch_get_track(tid) for tid in track_ids]
    
    # トラック検索
    # def fetch_search_tracks(self, query: str, limit: int = 20) -> list:
    #     params = {"q": query, "limit": limit}
    #     data = self._call_api("/search/track", params=params)
    #     return data.get("data", [])
    # 2026/04/19 SpotifyAPIは規約が厳しいので、deezerへ移行する準備だけ整えておく
    
    # 特定のアーティストに紐づく人気曲データ取得
    def fetch_get_artist_top_tracks(self, artist_id: str, limit: int = 5) -> list:
        params = {"limit": limit}
        data = self._call_api(f"/artist/{artist_id}/top", params=params)
        return data.get("data", [])
