from typing import List, Optional

import requests
from django.conf import settings

# --- コアモジュール ---
from core.exceptions.exceptions import ExternalServiceError


class SetlistFmService:
    """setlist.fm API から直近セットリスト情報を取得するサービス。"""

    BASE_URL = "https://api.setlist.fm/rest/1.0"

    def __init__(self):
        self.api_key = getattr(settings, "SETLIST_FM_APIKEY", "")

    def _headers(self):
        return {
            "x-api-key": self.api_key,
            "Accept": "application/json",
        }

    def get_artist_mbid(self, artist_name: str) -> Optional[str]:
        """アーティスト名から MBID を取得する。"""
        if not self.api_key or not artist_name:
            return None

        url = f"{self.BASE_URL}/search/artists"
        params = {"artistName": artist_name, "p": 1}

        response = requests.get(url, headers=self._headers(), params=params, timeout=10)
        if response.status_code != 200:
            return None

        artists = response.json().get("artist", [])
        if not artists:
            return None
        return artists[0].get("mbid")

    def get_latest_setlist_song_names(self, artist_name: str) -> List[str]:
        """
        指定アーティストの直近セットリストから曲名一覧を返す。
        取得できない場合は空配列を返す（生成処理継続のため）。
        """
        mbid = self.get_artist_mbid(artist_name)
        if not mbid:
            return []

        url = f"{self.BASE_URL}/artist/{mbid}/setlists"
        response = requests.get(url, headers=self._headers(), timeout=10)
        if response.status_code == 404:
            return []
        if response.status_code != 200:
            raise ExternalServiceError("setlist.fm API の呼び出しに失敗しました。")

        data = response.json()
        setlists = data.get("setlist", [])
        if not setlists:
            return []

        latest = setlists[0]
        songs: List[str] = []
        for set_block in latest.get("sets", {}).get("set", []):
            for song in set_block.get("song", []):
                name = song.get("name")
                if name:
                    songs.append(name)

        # 順序維持で重複除去
        return list(dict.fromkeys(songs))
