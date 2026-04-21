import requests
from typing import List, Optional
from django.conf import settings

# --- コアモジュール ---
from core.consts import LOG_METHOD
from core.utils.log_helpers import log_output_by_msg_id
from core.exceptions.exceptions import ExternalServiceError

# --- 共通モジュール ---
from apps.common.exceptions import SetlistNotFoundError, SetlistFmAPIAuthFailedException

class SetlistFmService:
    """Setlist.fm API サービス"""
    BASE_URL = "https://api.setlist.fm/rest/1.0"

    def __init__(self):
        self.api_key = getattr(settings, "SETLIST_FM_APIKEY", "")

    def _headers(self):
        return {
            "x-api-key": self.api_key,
            "Accept": "application/json",
        }

    def _call_api(self, endpoint: str, params: dict = None):
        """API実行用の共通ラッパー"""
        url = f"{self.BASE_URL}{endpoint}"
        
        # 開始ログ出力
        log_output_by_msg_id(
            log_id="MSGD001",
            params=[f"SetlistFmAPI/DEBUG: Calling {url} with {params}"],
            logger_name=LOG_METHOD.APPLICATION.value,
        )

        try:
            response = requests.get(url, headers=self._headers(), params=params, timeout=10)
            
            # APIエラー発生時、レスポンス内の情報を確認
            if response.status_code != 200:
                # ステータスコードごとのハンドリング
                if response.status_code == 401:
                    # 警告ログ出力
                    log_output_by_msg_id(
                        log_id="MSGW001",
                        params=[f"Setlist.fm API Auth Error: {response.status_code}"],
                        logger_name=LOG_METHOD.APPLICATION.value,
                    )
                    raise SetlistFmAPIAuthFailedException()

                if response.status_code == 403:
                    # 警告ログ出力
                    log_output_by_msg_id(
                        log_id="MSGW001",
                        params=[f"Setlist.fm API Auth Error: {response.status_code}"],
                        logger_name=LOG_METHOD.APPLICATION.value,
                    )
                    raise ExternalServiceError()
                
                if response.status_code == 404:
                    # 警告ログ出力
                    log_output_by_msg_id(
                        log_id="MSGW001",
                        params=[f"Setlist.fm API Not Found Error. url :{url} params: {str(params)}"],
                        logger_name=LOG_METHOD.APPLICATION.value,
                    )
                    raise ExternalServiceError()

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout as e:
            # 警告ログ出力
            log_output_by_msg_id(
                log_id="MSGW001",
                params=[f"Setlist.fm API Timeout."],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            raise ExternalServiceError() from e
        except requests.exceptions.RequestException as e:
            log_output_by_msg_id(
                log_id="MSGW001",
                params=[f"Setlist.fm API Error: {str(e)}"],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            raise ExternalServiceError() from e

    # ------------------------------------------------------------------
    # fetchメソッド群 (API通信)
    # ------------------------------------------------------------------
    def fetch_search_artists_by_artist_name(self, artist_name: str, page: int = 1) -> dict:
        """アーティスト名よりアーティストを検索"""
        return self._call_api(f"/search/artists", params={"artistName": artist_name, "p": page})

    def fetch_artist_setlists(self, mbid: str, page: int = 5) -> dict:
        """アーティストのセットリスト一覧を取得(例: [page]/全体 ずつ取得)"""
        # return self._call_api(f"/artist/{mbid}/setlists")
        return self._call_api(f"/artist/{mbid}/setlists", params={"p": page})

    # ------------------------------------------------------------------
    # ビジネスロジックメソッド
    # ------------------------------------------------------------------
    def get_latest_setlist_by_mbid(self, mbid: str) -> List[str]:
        """直近のセットリスト曲名一覧を取得する"""
        
        data = self.fetch_artist_setlists(mbid)
        
        setlists = data.get("setlist", [])
        if not setlists:
            # 警告ログ出力
            log_output_by_msg_id(
                log_id="MSGW001",
                params=[f"Setlist fetch result is Not Found Error."],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            raise SetlistNotFoundError()
        
        # 2026/4/19 直近1件だと見つからない場合が結構存在する
        # 直近(インデックス0)のセットリストを解析
        # latest = setlists[0]
        # songs: List[str] = []
        # sets -> set (list) -> song (list) の階層を安全にパース
        # sets_data = setlist.get("sets", {}).get("set", [])
        # for set_block in sets_data:
        #     for song in set_block.get("song", []):
        #         name = song.get("name")
        #         if name:
        #             songs.append(name)
        # 2026/4/19 直近1件だと見つからない場合が結構存在する

        for setlist in data["setlist"]:
            songs = []
            # sets -> set (list) -> song (list) の階層を安全にパース
            sets_data = setlist.get("sets", {}).get("set", [])
            for set_block in sets_data:
                for song in set_block.get("song", []):
                    name = song.get("name")
                    if name:
                        songs.append(name)
            
            if songs:
                # デバッグログ出力
                log_output_by_msg_id(
                    log_id="MSGD001",
                    params=[f"Setlist song is Exist. mbid: {mbid} setlist(eventDate): {setlist.get("eventDate")} setlist(venue): {setlist.get("venue",{}).get("name")}"],
                    logger_name=LOG_METHOD.APPLICATION.value,
                )
                for song in songs:
                    # デバッグログ出力
                    log_output_by_msg_id(
                        log_id="MSGD001",
                        params=[f"-  {song}"],
                        logger_name=LOG_METHOD.APPLICATION.value,
                    )
            else:
                # 警告ログ出力
                log_output_by_msg_id(
                    log_id="MSGW001",
                    params=[f"Setlist song is Not Found. mbid: {mbid} latest(eventDate): {setlist.get("eventDate")} latest(venue): {setlist.get("venue",{}).get("name")}"],
                    logger_name=LOG_METHOD.APPLICATION.value,
                )
                # raise SetlistNotFoundError() # 継続させる


        # 順序維持で重複除去
        return list(dict.fromkeys(songs))