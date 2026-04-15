from typing import List
import requests
import logging
from django.conf import settings
from apps.common.exceptions import SetlistNotFoundError
from core.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)

class SetlistFmService:
    """setlist.fm API からセットリスト情報を取得するサービス。"""

    BASE_URL = "https://api.setlist.fm/rest/1.0"

    def __init__(self):
        self.api_key = getattr(settings, "SETLIST_FM_APIKEY", "")
        if not self.api_key:
            logger.error("SETLIST_FM_APIKEY is not set in settings.")

    def _headers(self):
        return {
            "x-api-key": self.api_key,
            "Accept": "application/json",
        }

    def get_latest_setlist_by_mbid(self, mbid: str) -> List[str]:
        """
        MusicBrainz ID (MBID) を使用して、直近のセットリスト曲名一覧を取得する。
        
        Args:
            mbid (str): MusicBrainz ID
            
        Returns:
            List[str]: 曲名のリスト(重複なし、順序維持)
            
        Raises:
            SetlistNotFoundError: セットリストが存在しない場合
            ExternalServiceError: APIキー不足、通信エラー、API側の障害
        """
        if not self.api_key:
            # セットリスト取得サービスの準備ができていません。
            raise ExternalServiceError()

        url = f"{self.BASE_URL}/artist/{mbid}/setlists"

        try:
            response = requests.get(url, headers=self._headers(), timeout=10)

            # 404は「セットリストが1つも登録されていない」ケース
            if response.status_code == 404:
                raise SetlistNotFoundError()

            # 401/403はAPIキーの問題
            if response.status_code in [401, 403]:
                logger.error(f"Setlist.fm API Key Error: {response.status_code}")
                # 外部サービス認証エラーが発生しました。
                raise ExternalServiceError()

            response.raise_for_status()
            data = response.json()

            setlists = data.get("setlist", [])
            if not setlists:
                # セットリストが空の場合
                raise SetlistNotFoundError()

            # 直近(インデックス0)のセットリストを解析
            latest = setlists[0]
            songs: List[str] = []
            
            # sets -> set (list) -> song (list) の階層を安全にパース
            sets_data = latest.get("sets", {}).get("set", [])
            for set_block in sets_data:
                for song in set_block.get("song", []):
                    name = song.get("name")
                    if name:
                        songs.append(name)

            if not songs:
                # セットリストの枠組みはあるが曲が登録されていないケース
                # 最新の公演情報はありますが、曲目データが未登録です。
                raise SetlistNotFoundError()

            # 順序維持で重複除去(dict.fromkeys を利用)
            return list(dict.fromkeys(songs))

        except requests.exceptions.Timeout:
            # setlist.fm API への接続がタイムアウトしました。
            raise ExternalServiceError()
        except requests.exceptions.RequestException as e:
            logger.error(f"Setlist.fm API Connection Error: {str(e)}")
            # 外部サービスとの通信に失敗しました。
            raise ExternalServiceError()