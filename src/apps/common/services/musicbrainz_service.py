import requests
import logging
from django.core.cache import cache
from django.conf import settings
from apps.common.exceptions import ArtistMBIDNotFoundError
from core.exceptions.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)

class MusicBrainzService:
    """
    Spotify IDからMusicBrainzの情報を取得し、MBIDと英語名を特定するサービス。
    MusicBrainz API規約を遵守し、キャッシュと例外処理を統合。
    """
    BASE_URL = "https://musicbrainz.org/ws/2/url"
    
    # 規約: User-Agentに連絡先を含める(settingsから取るのが理想的)
    HEADERS = {
        "User-Agent": "SetlistSync/1.0.0 ( shogo@example.com )",
        "Accept": "application/json"
    }

    def get_artist_by_spotify_id(self, spotify_id: str) -> dict:
        """
        Spotify IDを元にMBIDと英語名を取得する。
        
        Args:
            spotify_id (str): SpotifyのアーティストID
            
        Returns:
            dict: { "mbid": str, "name": str, "sort_name": str }
            
        Raises:
            ArtistMBIDNotFoundError: MBIDが見つからない、または紐付けがない場合
            PlaylistExternalServiceError: 通信エラーやMusicBrainz側の障害
        """
        cache_key = f"mb_lookup_{spotify_id}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data

        # Spotify URLをMusicBrainzのリソースキーとして使用
        spotify_url = f"http://googleusercontent.com/spotify.com/5{spotify_id}"
        params = {
            "resource": spotify_url,
            "inc": "artist-rels",
            "fmt": "json"
        }

        try:
            response = requests.get(
                cls.BASE_URL, 
                params=params, 
                headers=cls.HEADERS, 
                timeout=7  # MB APIは少し重いことがあるため長めに設定
            )

            # --- ステータスコード別のハンドリング ---
            
            # MusicBrainz側のメンテナンスや過負荷 (502, 503, 504)
            if response.status_code >= 500:
                logger.error(f"MusicBrainz Server Error: {response.status_code}")
                # MusicBrainz APIが一時的に利用できません。
                raise ExternalServiceError()

            # URL(リソース)自体が存在しない場合、MusicBrainzは404を返す
            if response.status_code == 404:
                raise ArtistMBIDNotFoundError()

            # その他のエラーチェック
            response.raise_for_status()
            
            data = response.json()

            # relations配列から 'artist' ターゲットを抽出
            relations = data.get("relations", [])
            for rel in relations:
                if rel.get("target-type") == "artist":
                    artist_data = rel.get("artist", {})
                    
                    result = {
                        "mbid": artist_data.get("id"),
                        "name": artist_data.get("name"),       # 英語/標準名
                        "sort_name": artist_data.get("sort-name")
                    }

                    # 成功時のみキャッシュ保存(24時間)
                    cache.set(cache_key, result, 60 * 60 * 24)
                    return result
            
            # relationsの中にartist情報が含まれていない場合
            raise ArtistMBIDNotFoundError()

        except requests.exceptions.Timeout:
            logger.error(f"MusicBrainz Timeout: SpotifyID={spotify_id}")
            # MusicBrainz APIへの接続がタイムアウトしました。
            raise ExternalServiceError()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"MusicBrainz Connection Error: {str(e)}")
            # 外部サービスとの通信に失敗しました。
            raise ExternalServiceError()