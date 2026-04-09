from itertools import islice
from typing import Dict, List
from urllib.parse import quote

from apps.artist.models import T_Artist
from apps.common.models import T_FileResource
from apps.playlist.models import T_Playlist, T_PlaylistTrack
from django.db import transaction
from core.services.setlistfm_service import SetlistFmService
from core.services.spotify_service import SpotifyService


class PlaylistService:
    """
    プレイリスト生成・保存・差し替えを担当するサービス。

    役割:
    - setlist.fm + Spotify を使って候補曲を生成
    - 生成結果を T_Playlist / T_PlaylistTrack へ保存
    - Trackset 共有URLを作成
    """

    PATTERN_RATIOS = {
        "balanced": {"live": 0.3, "popular": 0.3, "recommend": 0.4},
        "live_focus": {"live": 0.6, "popular": 0.2, "recommend": 0.2},
        "popular_focus": {"live": 0.2, "popular": 0.6, "recommend": 0.2},
    }

    def __init__(self):
        self.spotify_service = SpotifyService()
        self.setlist_service = SetlistFmService()

    @staticmethod
    def _dedupe_keep_order(values: List[str]) -> List[str]:
        """
        入力:
        - values: 重複を含む可能性のある文字列配列
        出力:
        - 重複を除去しつつ、元順序を維持した配列
        副作用:
        - なし（純粋関数）
        """
        return list(dict.fromkeys([v for v in values if v]))

    def _take(self, values: List[str], n: int) -> List[str]:
        """
        入力:
        - values: 取得元配列
        - n: 取得件数（0未満は0扱い）
        出力:
        - 先頭から最大n件の配列
        副作用:
        - なし（純粋関数）
        """
        return list(islice(values, max(0, n)))

    def _mix_uris(
        self,
        pattern: str,
        total_count: int,
        live_uris: List[str],
        popular_uris: List[str],
        recommend_uris: List[str],
    ) -> List[str]:
        """
        入力:
        - pattern: 配合パターン（balanced/live_focus/popular_focus）
        - total_count: 返却したい最終曲数
        - live_uris/popular_uris/recommend_uris: ソース別URI配列
        出力:
        - 指定曲数に正規化されたURI配列
        副作用:
        - なし（純粋関数）
        """
        # 1. パターン別比率を決定（未知パターンはbalancedへフォールバック）
        ratios = self.PATTERN_RATIOS.get(pattern, self.PATTERN_RATIOS["balanced"])
        live_count = int(total_count * ratios["live"])
        popular_count = int(total_count * ratios["popular"])
        recommend_count = total_count - live_count - popular_count

        # 2. 比率分だけ各ソースから取り出す
        mixed = []
        mixed.extend(self._take(live_uris, live_count))
        mixed.extend(self._take(popular_uris, popular_count))
        mixed.extend(self._take(recommend_uris, recommend_count))

        # 3. 枠不足時は残り候補で補完
        if len(mixed) < total_count:
            rest = self._dedupe_keep_order(live_uris + popular_uris + recommend_uris)
            for uri in rest:
                if len(mixed) >= total_count:
                    break
                if uri not in mixed:
                    mixed.append(uri)

        return self._dedupe_keep_order(mixed)[:total_count]

    @staticmethod
    def create_spotify_tracksets(
        track_ids: List[str], title: str = "MyList", chunk_size: int = 50
    ) -> List[str]:
        """
        入力:
        - track_ids: Spotify曲ID配列
        - title: URL上のタイトル文字列
        - chunk_size: 1URLあたりの最大曲数（デフォルト50）
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

    def generate_playlist(self, user_profile, params: Dict) -> Dict:
        """
        入力:
        - user_profile: ログインユーザーのプロフィール
        - params: 生成条件（artist_ids, mood, pattern 等）
        出力:
        - 生成結果辞書（artists/tracks/sources）
        副作用:
        - なし（外部API呼び出しは行うがDB更新はしない）
        """
        # 1. 生成対象のアーティストをユーザー所有データから取得
        artist_ids = params["artist_ids"]
        selected_artists = list(
            T_Artist.objects.filter(
                id__in=artist_ids,
                user=user_profile,
                deleted_at__isnull=True,
            )
        )
        if not selected_artists:
            return {"tracks": [], "artists": []}

        # 2. パラメータを抽出
        popular_tracks_count = params["popular_tracks_count"]
        use_recent_setlist = params["use_recent_setlist"]
        mood_brightness = params["mood_brightness"]
        mood_intensity = params["mood_intensity"]
        pattern = params["pattern"]
        total_tracks = params["total_tracks"]

        # 1) 直近セトリ由来: ライブで演奏された可能性が高い曲を優先候補にする
        live_uris: List[str] = []
        if use_recent_setlist:
            for artist in selected_artists:
                song_names = self.setlist_service.get_latest_setlist_song_names(
                    artist.name
                )
                for song_name in song_names:
                    uri = self.spotify_service.search_track_uri(artist.name, song_name)
                    if uri:
                        live_uris.append(uri)
        live_uris = self._dedupe_keep_order(live_uris)

        # 2) 人気曲: 初見ユーザーでも聴きやすい入口曲を確保する
        popular_uris: List[str] = []
        for artist in selected_artists:
            popular_uris.extend(
                self.spotify_service.fetch_top_tracks(
                    artist.spotify_id,
                    limit=popular_tracks_count,
                )
            )
        popular_uris = self._dedupe_keep_order(popular_uris)

        # 3) ムード推薦: 明るさ/激しさを反映した補完候補を取得する
        seed_artists = [a.spotify_id for a in selected_artists if a.spotify_id][:5]
        recommend_uris = self.spotify_service.fetch_recommendation_tracks(
            seed_artists=seed_artists,
            target_valence=mood_brightness / 100.0,
            target_energy=mood_intensity / 100.0,
            limit=total_tracks,
        )
        recommend_uris = self._dedupe_keep_order(recommend_uris)

        # 4) パターン配合: 3ソースを指定比率で合成して最終候補を作る
        track_uris = self._mix_uris(
            pattern=pattern,
            total_count=total_tracks,
            live_uris=live_uris,
            popular_uris=popular_uris,
            recommend_uris=recommend_uris,
        )
        track_details = self.spotify_service.fetch_tracks_detail_by_uris(track_uris)

        # 5. APIレスポンス用に整形して返却
        return {
            "artists": [
                {"id": str(a.id), "name": a.name, "spotify_id": a.spotify_id}
                for a in selected_artists
            ],
            "tracks": track_details,
            "sources": {
                "live_set_tracks": len(live_uris),
                "popular_tracks": len(popular_uris),
                "recommended_tracks": len(recommend_uris),
            },
        }

    @transaction.atomic
    def create_generated_playlist(self, user_profile, params: Dict, kino_id: str):
        """
        入力:
        - user_profile: ログインユーザーのプロフィール
        - params: 生成条件 + 保存情報（title/image_id）
        - kino_id: 操作ログ/監査用の処理識別子
        出力:
        - (playlistインスタンス, trackset_urls)
        副作用:
        - T_Playlist / T_PlaylistTrack を新規作成（トランザクション内）
        """
        # 1. まず生成処理を行い、候補曲を取得
        generated = self.generate_playlist(user_profile=user_profile, params=params)

        # 2. 画像指定がある場合のみ参照を解決
        image = None
        if params.get("image_id"):
            image = T_FileResource.objects.filter(
                id=params["image_id"], deleted_at__isnull=True
            ).first()

        # 3. プレイリスト本体を作成
        playlist = T_Playlist.objects.create(
            user=user_profile,
            title=params["title"],
            image=image,
            spotify_id=None,
            created_by_id=user_profile.user_id,
            created_method=kino_id,
            updated_by_id=user_profile.user_id,
            updated_method=kino_id,
        )

        # 4. 生成対象アーティストをプレイリストに紐付け
        playlist.artists.set(
            T_Artist.objects.filter(
                id__in=params["artist_ids"], user=user_profile, deleted_at__isnull=True
            )
        )

        # 5. 生成曲をプレイリスト明細へ保存（Spotify ID保持）
        for track in generated["tracks"]:
            T_PlaylistTrack.objects.create(
                playlist=playlist,
                name=track.get("name") or "",
                artist=None,
                preview_url=track.get("preview_url"),
                spotify_id=track.get("spotify_id"),
                created_by_id=user_profile.user_id,
                created_method=kino_id,
                updated_by_id=user_profile.user_id,
                updated_method=kino_id,
            )

        # 6. 共有用Trackset URLを生成して返却
        track_ids = [
            track["spotify_id"] for track in generated["tracks"] if track.get("spotify_id")
        ]
        return playlist, self.create_spotify_tracksets(track_ids, params["title"])

    @transaction.atomic
    def replace_tracks(self, playlist: T_Playlist, track_ids: List[str], kino_id: str) -> Dict:
        """
        入力:
        - playlist: 更新対象プレイリスト
        - track_ids: 差し替え後のSpotify曲ID配列
        - kino_id: 操作ログ/監査用の処理識別子
        出力:
        - 差し替え結果辞書（updated_count, playlist_id）
        副作用:
        - 既存明細を論理削除し、新規明細を作成（トランザクション内）
        """
        # 1. 既存明細を論理削除
        old_tracks = playlist.playlist_t_playlist_track_set.filter(deleted_at__isnull=True)
        for row in old_tracks:
            row.deleted_at = row.updated_at
            row.updated_method = kino_id
            row.save()

        # 2. Spotify曲IDから詳細を取得
        uris = [f"spotify:track:{track_id}" for track_id in track_ids]
        details = self.spotify_service.fetch_tracks_detail_by_uris(uris)

        # 3. 新しい明細を作成
        created = 0
        for track in details:
            T_PlaylistTrack.objects.create(
                playlist=playlist,
                name=track.get("name") or "",
                artist=None,
                preview_url=track.get("preview_url"),
                spotify_id=track.get("spotify_id"),
                created_by_id=playlist.user.user_id,
                created_method=kino_id,
                updated_by_id=playlist.user.user_id,
                updated_method=kino_id,
            )
            created += 1

        # 4. 置換結果を返却
        return {"updated_count": created, "playlist_id": str(playlist.id)}

    def search_tracks(self, artist_spotify_id: str, q: str, limit: int = 20):
        """
        入力:
        - artist_spotify_id: 絞り込み対象アーティストのSpotify ID
        - q: 検索キーワード
        - limit: 最大取得件数
        出力:
        - 検索結果配列
        副作用:
        - なし（Spotify API呼び出しのみ）
        """
        return self.spotify_service.search_tracks(
            q=q,
            artist_spotify_id=artist_spotify_id,
            limit=limit,
        )
