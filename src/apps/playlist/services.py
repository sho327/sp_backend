from datetime import datetime
from itertools import islice
from typing import Dict, List
from urllib.parse import quote

from django.db import IntegrityError, transaction

# --- アカウントモジュール ---
from apps.account.models import M_User

# --- アーティストモジュール ---
from apps.artist.models import T_Artist

# --- 共通モジュール ---
from apps.common.models import T_FileResource
from apps.common.services.setlistfm_service import SetlistFmService
from apps.common.services.spotify_service import SpotifyService
from apps.playlist.exceptions import (
    InvalidPlaylistRequestError,
    PlaylistAlreadyExistsError,
    PlaylistCreateError,
    PlaylistError,
    PlaylistExternalServiceError,
    PlaylistNotFoundError,
    PlaylistReplaceError,
)

# --- プレイリストモジュール ---
from apps.playlist.models import R_PlaylistArtist, T_Playlist, T_PlaylistTrack

# --- コアモジュール ---
from core.utils.common import dedupe_keep_order, take


class PlaylistService:
    """
    プレイリスト生成/保存/差し替えを担当するサービスクラス。
    役割:
    - setlist.fm+Spotifyを使って候補曲を生成
    - 生成結果をT_Playlist/T_PlaylistTrackへ保存
    - Trackset共有URLを作成
    """

    def __init__(self):
        self.spotify_service = SpotifyService()
        self.setlist_service = SetlistFmService()

    # ------------------------------------------------------------------
    # 一覧取得系サービス
    # ------------------------------------------------------------------
    # プレイリスト一覧取得
    def list_artist(self, date_now: datetime, kino_id: str, user: M_User, title=None):
        """
        フィルタリングを考慮したプレイリスト一覧取得
        """
        # 1. 基本クエリ（自分かつ未削除 ＋ N+1対策）
        queryset = T_Playlist.objects.filter(
            user=user, deleted_at__isnull=True
        ).select_related("image")

        # 2. タイトルフィルター(部分一致)
        if title:
            queryset = queryset.filter(title__icontains=title)

        # 3. ソート
        queryset = queryset.order_by("-created_at")

        return queryset

    # ------------------------------------------------------------------
    # 詳細取得系サービス
    # ------------------------------------------------------------------
    # プレイリスト詳細取得
    def detail_playlist(
        self, date_now: datetime, kino_id: str, user: M_User, playlist_id: str
    ) -> T_Playlist:
        """
        特定のプレイリスト詳細を取得する(N+1対策済)
        """
        try:
            # 1. クエリセット構築
            # select_related: 画像
            # prefetch_related: アーティスト(ManyToManyField), トラック(逆参照)
            playlist = (
                T_Playlist.objects.filter(
                    id=playlist_id, user=user, deleted_at__isnull=True
                )
                .select_related("image")
                .prefetch_related(
                    "artists", "playlist_t_playlist_track_set"  # トラック一覧も取得
                )
                .get()
            )

            return playlist

        except T_Playlist.DoesNotExist:
            raise PlaylistNotFoundError()

    # ------------------------------------------------------------------
    # 登録系サービス
    # ------------------------------------------------------------------
    def create_playlist(
        self, date_now: datetime, kino_id: str, user: M_User, validated_data: dict
    ) -> T_Playlist:
        """プレイリストを新規登録する"""
        # 1. プレイリストの作成
        playlist = T_Playlist.objects.create(
            user=user,
            title=validated_data["title"],
            image=validated_data.get("image"),  # FileResourceインスタンス
            created_by=user,
            created_method=kino_id,
            updated_by=user,
            updated_method=kino_id,
        )

        # 3. アーティストとの紐付け(ManyToMany/R_PlaylistArtist)
        artists = validated_data.get("artists", [])
        if artists:
            relations = [
                R_PlaylistArtist(
                    playlist=playlist,
                    artist=artist,
                    created_by=user,
                    created_method=kino_id,
                    updated_by=user,
                    updated_method=kino_id,
                )
                for artist in artists
            ]
            R_PlaylistArtist.objects.bulk_create(relations)

        # 2. 初期トラックの登録（もしリクエストに含まれる場合）
        # tracks_data = [{"name": "Song A", "spotify_id": "xxx", "artist": <instance>}, ...]
        # tracks_data = validated_data.get('tracks', [])
        # if tracks_data:
        #     track_instances = [
        #         T_PlaylistTrack(
        #             playlist=playlist,
        #             name=track.get('name'),
        #             spotify_id=track.get('spotify_id'),
        #             artist=track.get('artist'), # T_Artistインスタンス
        #             created_by=user,
        #             created_method=kino_id,
        #             updated_by=user,
        #             updated_method=kino_id
        #         ) for track in tracks_data
        #     ]
        #     T_PlaylistTrack.objects.bulk_create(track_instances)

        return playlist

    # ------------------------------------------------------------------
    # 更新系サービス
    # ------------------------------------------------------------------
    # プレイリスト更新
    def update_playlist(
        self,
        date_now: datetime,
        kino_id: str,
        user: M_User,
        playlist_id: str,
        validated_data: dict,
    ) -> T_Playlist:
        """プレイリスト情報を更新する(洗替対応)"""
        # 1. 対象の取得（存在チェック）
        try:
            playlist: T_Playlist = T_Playlist.objects.select_for_update().get(
                id=playlist_id, user=user, deleted_at__isnull=True
            )
        except T_Playlist.DoesNotExist:
            raise PlaylistNotFoundError()

        # 2. タイトルの更新
        if "title" in validated_data:  # validated_dataに含まれているときのみ更新
            playlist.title = validated_data["title"]

        playlist.updated_method = kino_id
        playlist.updated_by = user
        playlist.save()

        # 3. アーティスト紐付けの更新(洗替方式)
        if "artist_ids" in validated_data:  # validated_dataに含まれているときのみ更新
            # 中間テーブルR_PlaylistArtistを物理削除
            R_PlaylistArtist.objects.filter(playlist=playlist).delete()

            new_artists = validated_data["artist_ids"]  # T_Artistインスタンスのリスト
            if new_artists:
                # bulk_create 用のリスト作成
                relations = [
                    R_PlaylistArtist(
                        playlist=playlist,
                        artist=artist,
                        created_by=user,
                        created_method=kino_id,
                        updated_by=user,
                        updated_method=kino_id,
                    )
                    for artist in new_artists
                ]
                R_PlaylistArtist.objects.bulk_create(relations)

        return playlist

    # ------------------------------------------------------------------
    # 削除系サービス
    # ------------------------------------------------------------------
    # プレイリスト削除
    def delete_playlist(
        elf, date_now: datetime, kino_id: str, user: M_User, playlist_id: str
    ):
        """プレイリストを論理削除する"""
        # 1. 対象の取得
        # 自分のデータ かつ すでに削除されていないものを対象にする
        try:
            playlist: T_Playlist = T_Playlist.objects.select_for_update().get(
                id=playlist_id, user=user, deleted_at__isnull=True
            )
        except T_Playlist.DoesNotExist:
            raise PlaylistNotFoundError()

        # 2. 論理削除処理
        # deleted_at を入れることで、以降のfilter(deleted_at__isnull=True)から除外される
        playlist.updated_by = user
        playlist.updated_method = kino_id
        playlist.deleted_at = date_now
        playlist.save()

        # 3. 関連データの整理
        # 中間テーブルは物理削除
        R_PlaylistArtist.objects.filter(playlist=playlist).delete()

        # プレイリストに紐づくトラックも論理削除(カスケード的に消す場合)
        T_PlaylistTrack.objects.filter(
            playlist=playlist, deleted_at__isnull=True
        ).update(
            updated_by=user,
            updated_method=kino_id,
            deleted_at=date_now,
        )

    # ------------------------------------------------------------------
    # その他サービス
    # ------------------------------------------------------------------
    # プレイリスト情報最新化(要: playlist_instance)※SpotifyAPI使用
    def refresh_playlist_tracks(
        self,
        date_now: datetime,
        kino_id: str,
        user: M_User,
        playlist_instance: T_Playlist,
    ):
        """
        プレイリスト内の各トラックが持つspotify_idを基に、
        Spotifyから最新の楽曲情報を取得してDBを更新する
        """
        # 1. 現在のプレイリストに含まれるトラック(spotify_idを持つもの)を取得
        current_tracks = (
            playlist_instance.playlist_t_playlist_track_set.filter(
                deleted_at__isnull=True
            )
            .exclude(spotify_id__isnull=True)
            .exclude(spotify_id="")
        )
        if not current_tracks.exists():
            return playlist_instance

        # 2. SpotifyIDの一括取得とFetch
        spotify_ids = list(current_tracks.values_list("spotify_id", flat=True))

        # 3. Spotify APIで楽曲情報を一括取得(fetch_get_tracksは内部でsp.tracksを使用)
        # ※一度に取得できる上限(通常50件)があるため、Service側で調整されている前提
        latest_tracks_data = self.spotify_service.fetch_get_tracks(spotify_ids)

        # 4. 取得データをマッピング(SpotifyIDをキーにした辞書)
        latest_map = {track["id"]: track for track in latest_tracks_data if track}

        # 5. 最新データに含まれる全アーティストIDを抽出した上でDB検索(N+1対策)
        new_artist_spotify_ids = set()
        for track_info in latest_tracks_data:
            if track_info and track_info.get("artists"):
                # 最初のアーティストをメインとして扱う
                new_artist_spotify_ids.add(track_info["artists"][0]["id"])

        # 自社DBに存在するアーティストを辞書化{spotify_id: T_Artistインスタンス}
        registered_artists_map = {
            a.spotify_id: a
            for a in T_Artist.objects.filter(
                user=user,
                spotify_id__in=new_artist_spotify_ids,
                deleted_at__isnull=True,
            )
        }

        # 6. DBの各レコードを最新データで更新
        for db_track in current_tracks:
            latest = latest_map.get(db_track.spotify_id)
            if not latest:
                continue

            # 名前や最新の情報を上書き
            db_track.name = latest.get("name", db_track.name)

            if latest.get("artists"):
                spotify_artist_id = latest["artists"][0]["id"]
                # 自社DBに存在すればセット(いなければNoneまたは現状維持)
                if spotify_artist_id in registered_artists_map:
                    db_track.artist = registered_artists_map[spotify_artist_id]

            db_track.updated_by = user
            db_track.updated_method = kino_id
            db_track.save()

        # 6. プレイリスト本体の更新
        playlist_instance.updated_by = user
        playlist_instance.updated_method = kino_id
        playlist_instance.save()

        return playlist_instance

    # プレイリスト情報最新化(要: playlist_instance)※SpotifyAPI使用
    # def refresh_playlist_tracks(self, date_now: datetime, kino_id: str, user: M_User, playlist_instance: T_Playlist):
    #     """
    #     プレイリスト内の各トラックが持つ spotify_id を基に、
    #     Spotifyから最新の楽曲情報を取得してDBを更新する
    #     """
    #     # 1. 現在のプレイリストに含まれるトラック(spotify_idを持つもの)を取得
    #     current_tracks = playlist_instance.playlist_t_playlist_track_set.filter(
    #         deleted_at__isnull=True
    #     ).exclude(spotify_id__isnull=True).exclude(spotify_id="")
    #     if not current_tracks.exists():
    #         return playlist_instance

    #     # 2. Spotify IDの一覧を作成
    #     spotify_ids = list(current_tracks.values_list('spotify_id', flat=True))

    #     # 3. Spotify APIで楽曲情報を一括取得(fetch_get_tracksは内部でsp.tracksを使用)
    #     # ※一度に取得できる上限(通常50件)があるため、Service側で調整されている前提
    #     latest_tracks_data = self.spotify_service.fetch_get_tracks(spotify_ids)

    #     # 4. 取得データをマッピング(SpotifyIDをキーにした辞書)
    #     latest_map = {track['id']: track for track in latest_tracks_data if track}

    #     # 5. 最新データに含まれる全アーティストIDを抽出した上でDB検索(N+1対策)
    #     new_artist_spotify_ids = set()
    #     for track_info in latest_tracks_data:
    #         if track_info and track_info.get('artists'):
    #             # 最初のアーティストをメインとして扱う
    #             new_artist_spotify_ids.add(track_info['artists'][0]['id'])

    #     # 自社DBに存在するアーティストを辞書化 {spotify_id: T_Artistインスタンス}
    #     registered_artists_map = {
    #         a.spotify_id: a for a in T_Artist.objects.filter(
    #             user=user,
    #             spotify_id__in=new_artist_spotify_ids,
    #             deleted_at__isnull=True
    #         )
    #     }

    #     # 6. DBの各レコードを最新データで更新
    #     for db_track in current_tracks:
    #         latest = latest_map.get(db_track.spotify_id)
    #         if not latest:
    #             continue

    #         # 名前や最新の情報を上書き
    #         db_track.name = latest.get('name', db_track.name)

    #         if latest.get('artists'):
    #             spotify_artist_id = latest['artists'][0]['id']
    #             # 自社DBに存在すればセット(いなければNoneまたは現状維持)
    #             if spotify_artist_id in registered_artists_map:
    #                 db_track.artist = registered_artists_map[spotify_artist_id]

    #         db_track.updated_by = user
    #         db_track.updated_method = kino_id
    #         db_track.save()

    #     # 6. プレイリスト本体の更新
    #     playlist_instance.updated_by = user
    #     playlist_instance.updated_method = kino_id
    #     playlist_instance.save()

    #     return playlist_instance

    # プレイリスト情報最新化(要: playlist_track_instance)※SpotifyAPI使用
    def refresh_playlist_track(
        self,
        date_now: datetime,
        kino_id: str,
        user: M_User,
        playlist_track_instance: T_PlaylistTrack,
    ):
        """
        特定のT_PlaylistTrackインスタンスをSpotifyIDを基に最新化する
        """
        if not playlist_track_instance.spotify_id:
            return playlist_track_instance

        # 1. Spotify から 1 件取得
        latest_data = self.spotify_service.fetch_get_track(
            playlist_track_instance.spotify_id
        )
        if not latest_data:
            return playlist_track_instance

        # 2. 基本情報の更新
        playlist_track_instance.name = latest_data.get(
            "name", playlist_track_instance.name
        )

        # 3. アーティスト紐付けの試行
        if latest_data.get("artists"):
            spotify_artist_id = latest_data["artists"][0]["id"]

            # 自社 DB に登録されているか確認
            try:
                # ユーザーに紐づく有効なアーティストを検索
                artist = T_Artist.objects.get(
                    user=user, spotify_id=spotify_artist_id, deleted_at__isnull=True
                )
                playlist_track_instance.artist = artist
            except T_Artist.DoesNotExist:
                # 登録されていなければ紐付けは行わない(既存の紐付けを維持するかは要件次第)
                pass

        playlist_track_instance.updated_by = user
        playlist_track_instance.updated_method = kino_id
        playlist_track_instance.save()

        return playlist_track_instance

    # プレイリスト生成※SpotifyAPI使用
    def generate_playlist_tracks(
        self, date_now: datetime, kino_id: str, user: M_User, validated_data: dict
    ) -> T_Playlist:
        """プレイリストを生成する"""
        # 1. プレイリストの作成
        playlist = self.create_playlist(date_now, kino_id, user, validated_data)

        # 2. パラメータを抽出
        generate_pattern = validated_data["popular_tracks_count"]
