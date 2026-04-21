import requests
from typing import List, Dict
from django.conf import settings

# --- コアモジュール ---
from core.consts import LOG_METHOD
from core.utils.log_helpers import log_output_by_msg_id
from core.exceptions.exceptions import ExternalServiceError

class LastfmService:
    """Last.fm API サービス"""
    BASE_URL = "http://ws.audioscrobbler.com/2.0/"

    def __init__(self):
        self.api_key = getattr(settings, "LASTFM_APIKEY", "")

    def _call_api(self, method: str, params: dict = None) -> dict:
        """
        API実行・エラーハンドリング・ログ出力の共通ラッパー
        Last.fmはクエリパラメータでmethodを指定する仕様
        """
        if params is None:
            params = {}
        
        # 必須パラメータの設定
        params.update({
            "method": method,
            "api_key": self.api_key,
            "format": "json"
        })

        # デバッグログ
        log_output_by_msg_id(
            log_id="MSGD001",
            params=[f"LastfmAPI/DEBUG: Calling {method} with {params}"],
            logger_name=LOG_METHOD.APPLICATION.value,
        )

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            
            # Last.fmはエラー時もステータス200を返すことがあるため、JSON内の"error"キーを確認
            data = response.json()
            if "error" in data:
                log_output_by_msg_id(
                    log_id="MSGW001",
                    params=[f"Last.fm API Error: {data.get('message')}"],
                    logger_name=LOG_METHOD.APPLICATION.value,
                )
                # エラーコードに応じた例外処理を適宜追加してください
                raise ExternalServiceError()

            if response.status_code != 200:
                log_output_by_msg_id(
                    log_id="MSGW001",
                    params=[f"Last.fm API Status Error: {response.status_code}"],
                    logger_name=LOG_METHOD.APPLICATION.value,
                )
                raise ExternalServiceError()

            return data

        except requests.exceptions.RequestException as e:
            log_output_by_msg_id(
                log_id="MSGW001",
                params=[f"Last.fm API Connection Error: {str(e)}"],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            raise ExternalServiceError() from e

    # ------------------------------------------------------------------
    # fetchメソッド群
    # ------------------------------------------------------------------
    def search_artist(self, artist_name: str) -> List[Dict]:
        """アーティスト検索"""
        data = self._call_api("artist.search", params={"artist": artist_name})
        # 構造: results -> artistmatches -> artist -> [list]
        return data.get("results", {}).get("artistmatches", {}).get("artist", [])

    def get_similar_artists(self, artist_name: str, limit: int = 10) -> List[Dict]:
        """関連アーティスト取得"""
        data = self._call_api("artist.getsimilar", params={"artist": artist_name, "limit": limit})
        # 構造: similarartists -> artist -> [list]
        return data.get("similarartists", {}).get("artist", [])
    
    def get_canonical_artist_name(self, artist_name: str) -> str | None:
        """
        アーティスト名からLast.fm側の正式名を1件取得する
        検索結果が空の場合は None を返す
        """
        # limit=1 を指定して、最初の一致結果のみを効率的に取得
        params = {"artist": artist_name, "limit": 1}
        data = self._call_api("artist.search", params=params)
        
        matches = data.get("results", {}).get("artistmatches", {}).get("artist", [])
        
        # 検索結果がリストかdictかによって挙動が変わる場合があるため安全に処理
        if isinstance(matches, list) and len(matches) > 0:
            return matches[0].get("name")
        elif isinstance(matches, dict) and matches:
            # limit=1を指定しても、APIの仕様で稀に単一のdictとして返るケースへの対応
            return matches.get("name")
            
        return None


# Last.fmで探したアーティスト名を基にIDを取得するフロー
# LastfmServiceのsearch_artist("Artist Name")で正確な名前を取得。

# 必要に応じてMusicBrainzServiceを使用し、
# 名前(またはURL)からMBID(MusicBrainz ID)を取得(これは既に実装済みですね)

# その情報を基に、各プラットフォームのAPIへ接続する
# Service（SpotifyServiceやDeezerService）を作成し、ID変換を行う。

# 例えば、LastfmServiceの結果からアーティスト名を得て、
# それをSpotifyの検索API（searchエンドポイント）に投げてspotify_idを取得するという流れになるかと思います。

# もし必要であれば、SpotifyServiceやDeezerServiceのID変換用のラッパーテンプレートも作成可能です。必要になった際はお声がけください。
