from collections import defaultdict
from datetime import datetime
from typing import List

from django.db.models import Q, Sum, Value
from django.db.models.functions import Coalesce

# --- アカウントモジュール ---
from apps.account.models import M_User
from apps.common.exceptions import SetlistNotFoundError

# --- 共通モジュール ---
from apps.common.models import T_FileResource
from apps.common.services.deezer_service import DeezerService
from apps.common.services.lastfm_service import LastfmService
from apps.common.services.musicbrainz_service import MusicBrainzService
from apps.common.services.setlistfm_service import SetlistFmService
from apps.common.services.spotify_service import SpotifyService
from apps.common.services.storage_service import StorageService
from apps.playlist.exceptions import (
    PlaylistNotFoundError,
    PlaylistTrackAlreadyExistsError,
    PlaylistTrackNotFoundError,
)

# --- プレイリストモジュール ---
from apps.playlist.models import R_PlaylistArtist, T_Playlist, T_PlaylistTrack

# --- コアモジュール ---
from core.consts import LOG_METHOD
from core.exceptions.exceptions import ApplicationError
from core.utils.log_helpers import log_output_by_msg_id
from core.utils.thread_pool_executor import executor


class PlaylistService:
    """
    プレイリスト生成/保存/差し替えを担当するサービスクラス。
    役割:
    - SetlistFm/Spotifyを使って候補曲を生成
    - 生成結果をT_Playlist/T_PlaylistTrackへ保存
    - Trackset共有URLを作成
    """

    def __init__(self):
        self.spotify_service = SpotifyService()
        self.deezer_service = DeezerService()
        self.setlist_service = SetlistFmService()
        self.storage_service = StorageService()
        self.musicbrainz_service = MusicBrainzService()
        self.lastfm_service = LastfmService()

    def _format_spotify_track(self, track: dict) -> dict:
        """Spotifyのレスポンスを共通フォーマットに変換するプライベートメソッド"""
        popularity = track.get("popularity")
        album = track.get("album") or {}
        return {
            "spotify_id": track.get("id"),
            "spotify_name": track.get("name"),
            "spotify_isrc": track.get("external_ids", {}).get("isrc"),
            "spotify_artist_name": track.get("artists", [{}])[0].get("name"),
            "spotify_popularity": popularity if popularity is not None else 0,
            "spotify_duration_ms": track.get("duration_ms"),
            "spotify_album_type": album.get("album_type"),
            "spotify_album_id": album.get("id"),
            "spotify_album_name": album.get("name"),
            "spotify_release_date": album.get("release_date"),
        }

    # ------------------------------------------------------------------
    # 一覧取得系サービス
    # ------------------------------------------------------------------
    # プレイリスト一覧取得
    def list_playlist(self, date_now: datetime, kino_id: str, user: M_User, title=None):
        """
        フィルタリングを考慮したプレイリスト一覧取得
        """
        # 1. 基本クエリ(自分かつ未削除/N+1対策)
        queryset = (
            T_Playlist.objects.filter(
                user=user,
                deleted_at__isnull=True,
            )
            .select_related("image")
            .annotate(
                # 合計時間の計算(trackが0件なら0を返すようにCoalesceで保護)
                total_spotify_duration_ms=Coalesce(
                    Sum(
                        "playlist_t_playlist_track_set__spotify_duration_ms",
                        filter=Q(
                            playlist_t_playlist_track_set__deleted_at__isnull=True
                        ),
                    ),
                    Value(0),
                )
            )
        )

        # 2. タイトルフィルター(部分一致)
        if title:
            queryset = queryset.filter(title__icontains=title)

        # 3. ソート
        queryset = queryset.order_by("-created_at")

        return queryset

    # ------------------------------------------------------------------
    # 詳細取得系サービス
    # ------------------------------------------------------------------
    # プレイリスト詳細取得
    def detail_playlist(
        self, date_now: datetime, kino_id: str, user: M_User, playlist_id: str
    ) -> T_Playlist:
        """
        特定のプレイリスト詳細を取得する(N+1対策済)
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
                .prefetch_related("artists", "playlist_t_playlist_track_set")
                .annotate(
                    total_spotify_duration_ms=Coalesce(
                        Sum(
                            "playlist_t_playlist_track_set__spotify_duration_ms",
                            filter=Q(
                                playlist_t_playlist_track_set__deleted_at__isnull=True
                            ),
                        ),
                        Value(0),
                    )
                )
                .get()
            )

            return playlist

        except T_Playlist.DoesNotExist:
            raise PlaylistNotFoundError()

    # ------------------------------------------------------------------
    # 登録系サービス
    # ------------------------------------------------------------------
    # プレイリスト登録
    def create_playlist(
        self, date_now: datetime, kino_id: str, user: M_User, validated_data: dict
    ) -> T_Playlist:
        """プレイリストを新規登録する"""
        # 1. 画像の保存
        upload_path = None
        if validated_data.get("image"):
            upload_path = self.storage_service.upload_file(
                file_data=validated_data["image"].file,
                folder_path="playlists",
                original_filename=validated_data["image"].name,
            )

        try:
            # 2. 画像リソースの作成
            file_resource = None
            if upload_path:
                file_resource = T_FileResource.objects.create(
                    file_type=T_FileResource.FileType.IMAGE,
                    file_data=upload_path,
                    file_name=f"playlist_{validated_data.get('title')}_image",
                    created_by=user,
                    created_method=kino_id,
                    updated_by=user,
                    updated_method=kino_id,
                )

            # 3. プレイリストの作成
            playlist = T_Playlist.objects.create(
                user=user,
                title=validated_data["title"],
                image=file_resource,
                created_by=user,
                created_method=kino_id,
                updated_by=user,
                updated_method=kino_id,
            )

            # 4. アーティストとの紐付け(ManyToMany/R_PlaylistArtist)
            artists = validated_data.get("artist_ids", [])
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

            # 5. 初期トラックの登録(もしリクエストに含まれる場合)
            tracks = validated_data.get("tracks", [])
            if tracks:
                track_instances = [
                    T_PlaylistTrack(
                        playlist=playlist,
                        created_by=user,
                        created_method=kino_id,
                        updated_by=user,
                        updated_method=kino_id,
                        **track,
                    )
                    for track in tracks
                ]
                T_PlaylistTrack.objects.bulk_create(track_instances)

            return playlist
        except Exception as e:
            # 保存した画像を削除
            if upload_path:
                self.storage_service.delete_file(upload_path)
            raise e

    # プレイリストトラック追加
    def add_playlist_track(
        self,
        date_now: datetime,
        kino_id: str,
        user: M_User,
        playlist_id: str,
        validated_data: dict,
    ) -> T_Playlist:
        """プレイリストへトラックを追加する"""
        # 1. 対象の取得(存在チェックとロック)
        try:
            playlist: T_Playlist = T_Playlist.objects.select_for_update().get(
                id=playlist_id,
                user=user,
                deleted_at__isnull=True,
            )
        except T_Playlist.DoesNotExist:
            raise PlaylistNotFoundError()

        # 既に同一のspotify_idが存在するかチェック
        spotify_id = validated_data.get("spotify_id")
        if T_PlaylistTrack.objects.filter(
            playlist=playlist,
            spotify_id=spotify_id,
            deleted_at__isnull=True,  # 論理削除されていないもののみチェック
        ).exists():
            raise PlaylistTrackAlreadyExistsError()

        # 2. プレイリストトラックの登録
        track = T_PlaylistTrack.objects.create(
            playlist=playlist,
            created_by=user,
            created_method=kino_id,
            updated_by=user,
            updated_method=kino_id,
            **validated_data,
        )

        # 3. 親プレイリストの更新
        # トラックが追加されたことを親にも反映させる
        playlist.updated_by = user
        playlist.updated_method = kino_id
        playlist.save()

        return track

    # ------------------------------------------------------------------
    # 更新系サービス
    # ------------------------------------------------------------------
    # プレイリスト更新
    def update_playlist(
        self,
        date_now: datetime,
        kino_id: str,
        user: M_User,
        playlist_id: str,
        validated_data: dict,
    ) -> T_Playlist:
        """プレイリスト情報を更新する(洗替対応)"""
        # 1. 対象の取得(存在チェック)
        try:
            playlist: T_Playlist = T_Playlist.objects.select_for_update().get(
                id=playlist_id, user=user, deleted_at__isnull=True
            )
        except T_Playlist.DoesNotExist:
            raise PlaylistNotFoundError()

        # 2. 旧インスタンスの退避 (ForeignKeyなのでインスタンスごと保持)
        old_image_instance = playlist.image

        # 3. 新規画像のアップロードとレコード作成
        new_image_instance = None
        upload_path = None
        if "image" in validated_data:
            upload_path = self.storage_service.upload_file(
                file_data=validated_data["image"].file,
                folder_path="playlists",
                original_filename=validated_data["image"].name,
            )

        try:
            # 4. 画像の更新
            if upload_path:
                new_image_instance = T_FileResource.objects.create(
                    file_type=T_FileResource.FileType.IMAGE,
                    file_data=upload_path,
                    file_name=f"playlist_{validated_data.get('title', playlist.title)}_image",
                    created_by=user,
                    created_method=kino_id,
                    updated_by=user,
                    updated_method=kino_id,
                )

            if new_image_instance:
                playlist.image = new_image_instance

            # 5. タイトルの更新
            if "title" in validated_data:  # validated_dataに含まれているときのみ更新
                playlist.title = validated_data["title"]

            playlist.updated_method = kino_id
            playlist.updated_by = user
            playlist.save()

            # 6. アーティスト紐付けの更新(洗替方式)
            # validated_dataに含まれているときのみ更新
            if "artist_ids" in validated_data:
                # 中間テーブルR_PlaylistArtistを物理削除
                R_PlaylistArtist.objects.filter(playlist=playlist).delete()

                new_artists = validated_data[
                    "artist_ids"
                ]  # T_Artistインスタンスのリスト
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

            # 7. トラック紐付けの更新(洗替方式)
            if "tracks" in validated_data:
                # 中間テーブルT_PlaylistArtistを物理削除
                T_PlaylistTrack.objects.filter(playlist=playlist).delete()

                tracks_data = validated_data["tracks"]  # trackのリスト
                track_instances = [
                    T_PlaylistTrack(
                        playlist=playlist,
                        created_by=user,
                        created_method=kino_id,
                        updated_by=user,
                        updated_method=kino_id,
                        **track,
                    )
                    for track in tracks_data
                ]
                T_PlaylistTrack.objects.bulk_create(track_instances)

            # 8. 旧画像のクリーンアップ(成功後に実行)
            if old_image_instance:
                # 物理ファイルの削除
                if old_image_instance and old_image_instance.file_data:
                    # ここで渡すのは`file_data.name`(相対パス)
                    # 例: "playlists/uuid.png"
                    self.storage_service.delete_file(old_image_instance.file_data.name)

                # DBレコードの削除(これにより紐付けが外れたレコードが残るのを防ぐ)
                old_image_instance.delete()

            return playlist
        except Exception as e:
            # 保存した画像を削除
            if upload_path:
                self.storage_service.delete_file(upload_path)
            raise e

    # ------------------------------------------------------------------
    # 削除系サービス
    # ------------------------------------------------------------------
    # プレイリスト削除
    def delete_playlist(
        self, date_now: datetime, kino_id: str, user: M_User, playlist_id: str
    ):
        """プレイリストを論理削除する"""
        # 1. 対象の取得
        # 自分のデータかつすでに削除されていないものを対象にする
        try:
            playlist: T_Playlist = T_Playlist.objects.select_for_update().get(
                id=playlist_id,
                user=user,
                deleted_at__isnull=True,
            )
        except T_Playlist.DoesNotExist:
            raise PlaylistNotFoundError()

        # 2. 関連データの整理
        # トラックの論理削除(先に行うことで、親がいなくなった後にトラックが浮くのを防ぐ)
        T_PlaylistTrack.objects.filter(
            playlist=playlist, deleted_at__isnull=True
        ).update(
            updated_by=user,
            updated_method=kino_id,
            deleted_at=date_now,
        )

        # 中間テーブルは物理削除
        R_PlaylistArtist.objects.filter(playlist=playlist).delete()

        # 3. プレイリスト本体の論理削除
        # deleted_at を入れることで、以降のfilter(deleted_at__isnull=True)から除外される
        playlist.updated_by = user
        playlist.updated_method = kino_id
        playlist.deleted_at = date_now
        playlist.save()

        # 4. 画像の削除
        # ※ファイル削除はロールバックできないため、最後に実行するのが鉄則
        playlist_image_instance = playlist.image
        if playlist_image_instance and playlist_image_instance.file_data:
            # ここで渡すのは`file_data.name`(相対パス)
            # 例: "playlists/uuid.png"
            self.storage_service.delete_file(playlist_image_instance.file_data.name)

    # プレイリストトラック削除
    def remove_playlist_track(
        self,
        date_now: datetime,
        kino_id: str,
        user: M_User,
        playlist_id: str,
        track_id: str,
    ):
        """プレイリスト内のトラックを削除する"""
        # 1. プレイリストの存在チェック
        playlist = T_Playlist.objects.filter(
            id=playlist_id, user=user, deleted_at__isnull=True
        ).first()
        if not playlist:
            raise PlaylistNotFoundError()

        # 2. 対象の取得(プレイリストトラック/存在チェック)
        track = None
        try:
            # ロックを取得
            track = T_PlaylistTrack.objects.select_for_update().get(
                id=track_id,
                playlist_id=playlist_id,
                deleted_at__isnull=True,
            )
        except T_PlaylistTrack.DoesNotExist:
            raise PlaylistTrackNotFoundError()

        # 3. 論理削除処理
        track.updated_by = user
        track.updated_method = kino_id
        track.deleted_at = date_now
        track.save()

        # 4. 親プレイリストの更新(履歴管理のため)
        playlist.updated_by = user
        playlist.updated_method = kino_id
        playlist.save()

        return track

    # ------------------------------------------------------------------
    # その他サービス
    # ------------------------------------------------------------------
    # プレイリスト情報最新化(要: playlist_instance)※SpotifyAPI使用
    def refresh_playlist_tracks(
        self,
        date_now: datetime,
        kino_id: str,
        user: M_User,
        playlist_instance: T_Playlist,
    ):
        """
        プレイリスト内の各トラックをSpotifyAPIで取得した最新情報で一括更新する
        """
        # 1. 現在のプレイリストに含まれるトラック(spotify_idを持つもの)を取得
        current_tracks = (
            playlist_instance.playlist_t_playlist_track_set.filter(
                deleted_at__isnull=True
            )
            .exclude(spotify_id__isnull=True)
            .exclude(spotify_id="")
        )
        if not current_tracks.exists():
            return playlist_instance

        # 2. SpotifyAPIで楽曲情報を一括取得
        spotify_ids = list(current_tracks.values_list("spotify_id", flat=True))

        # 3. SpotifyAPIで楽曲情報を一括取得(fetch_get_tracksは内部でsp.tracksを使用)
        # ※一度に取得できる上限(通常50件)があるため、Service側で調整されている前提
        # latest_tracks_data = self.spotify_service.fetch_get_tracks(spotify_ids)
        # latest_map = {track["id"]: track for track in latest_tracks_data if track}

        # 2026/4/19 fetch_get_tracksはSpotifyAPIにて使用不可の為、fetch_get_trackを並列実行させる形に変更
        # executor.mapはリストの順序を保持して結果を返す
        # 戻り値は [track_data, track_data, None, track_data...] となります
        results = list(executor.map(self.spotify_service.fetch_get_track, spotify_ids))
        # 2026/4/19 fetch_get_tracksはSpotifyAPIにて使用不可の為、fetch_get_trackを並列実行させる形に変更

        # Noneを除外してマップ作成
        latest_map = {res["id"]: res for res in results if res and "id" in res}

        # 3. インスタンスの値を更新
        updated_tracks = []
        for db_track in current_tracks:
            latest = latest_map.get(db_track.spotify_id)
            if not latest:
                continue

            # APIレスポンスから必要なデータを抽出
            album = latest.get("album") or {}

            # 各種フィールドの同期
            db_track.spotify_name = latest.get("name", db_track.spotify_name)
            db_track.spotify_isrc = latest.get("external_ids", {}).get(
                "isrc", db_track.spotify_isrc
            )
            db_track.spotify_artist_name = latest.get("artists", [{}])[0].get(
                "name", db_track.spotify_artist_name
            )

            # Noneなら0にする
            popularity = latest.get("popularity")
            db_track.spotify_popularity = popularity if popularity is not None else 0

            db_track.duration_ms = latest.get(
                "duration_ms", db_track.spotify_duration_ms
            )
            db_track.spotify_album_type = album.get(
                "album_type", db_track.spotify_album_type
            )
            db_track.spotify_album_id = album.get("id", db_track.spotify_album_id)
            db_track.spotify_album_name = album.get("name", db_track.spotify_album_name)
            db_track.spotify_release_date = album.get(
                "release_date", db_track.spotify_release_date
            )

            db_track.updated_by = user
            db_track.updated_method = kino_id

            updated_tracks.append(db_track)

        # 4. bulk_updateで一括保存
        if updated_tracks:
            T_PlaylistTrack.objects.bulk_update(
                updated_tracks,
                [
                    "spotify_name",
                    "spotify_isrc",
                    "spotify_artist_name",
                    "spotify_popularity",
                    "spotify_duration_ms",
                    "spotify_album_type",
                    "spotify_album_id",
                    "spotify_album_name",
                    "spotify_release_date",
                    "updated_by",
                    "updated_method",
                ],
            )

        # 5. プレイリスト本体の更新
        playlist_instance.updated_by = user
        playlist_instance.updated_method = kino_id
        playlist_instance.save()

        return playlist_instance

    # プレイリスト生成※SpotifyAPI使用
    def generate_tracks(
        self,
        date_now: datetime,
        kino_id: str,
        user: M_User,
        validated_data: dict,
    ) -> List[dict]:
        """各種パターンに基づいてトラックデータを生成する"""
        # 1. パラメータを抽出
        pattern = validated_data["pattern"]
        track_count = validated_data["get_tracks_count"]
        original_artists = validated_data[
            "artists"
        ]  # リストではなくオブジェクトのリストとして受け取る
        related_artists_count = validated_data["related_artists_count"]

        # 1. 処理対象アーティストリストの構築(オリジナル+関連アーティスト)
        processing_queue = []

        # オリジナルの追加
        for artist in original_artists:
            processing_queue.append(artist)

        # 関連アーティストの集計処理
        # キー: アーティスト名, 値: スコア合計
        related_artist_scores = defaultdict(float)

        # 既存のアーティスト名のリスト（除外用）
        original_names = {a["name"] for a in original_artists}

        # 関連アーティストの追加
        for artist in original_artists:
            try:
                artist_name = artist["name"]
                # 1. LastFM側を検索し正式名称を取得
                l_artist_name = self.lastfm_service.get_canonical_artist_name(
                    artist_name
                )
                if not l_artist_name:
                    continue

                # 関連アーティストを10件ずつ取得
                # Last.fm APIの "match" フィールドを利用
                l_artists = self.lastfm_service.get_similar_artists(
                    l_artist_name, limit=10
                )

                for l_artist in l_artists:
                    # 既に選択されているアーティストは関連として追加しない
                    if l_artist["name"] in original_names:
                        continue

                    # スコアを加算 (Last.fmの match は文字列の数値なのでfloatに変換)
                    score = float(l_artist.get("match", 0))
                    related_artist_scores[l_artist["name"]] += score

            except Exception as e:
                # ここでログを出して、失敗したアーティストはスキップし、次の処理へ継続
                log_output_by_msg_id(
                    log_id="MSGW001",
                    params=[
                        f"Warning: Failed to fetch related artists for {artist['name']}: {str(e)}"
                    ],
                    logger_name=LOG_METHOD.APPLICATION.value,
                )
                continue

        # 2. スコアでソートして関連アーティストの上位を抽出
        # items = [("アーティスト名", スコア), ...]
        sorted_related = sorted(
            related_artist_scores.items(), key=lambda x: x[1], reverse=True
        )
        top_related = sorted_related[:related_artists_count]

        # 3. 上位の関連アーティストをDeezerで検索してキューに追加
        for name, score in top_related:
            try:
                # Deezerで検索してIDを取得
                deezer_results = self.deezer_service.fetch_search_artists(
                    query=name, limit=1
                )
                if not deezer_results:
                    continue

                # 検索結果をデータ構造に合わせて追加
                deezer_artist = deezer_results[0]
                processing_queue.append(
                    {
                        "name": deezer_artist["name"],
                        "deezer_id": str(deezer_artist["id"]),
                        "setlistfm_mbid": None,  # 必要に応じてMBID検索を行う
                        "need_mbid_fetch": True,
                    }
                )

            except Exception as e:
                # Deezer検索失敗時も、他のアーティスト処理を止めない
                log_output_by_msg_id(
                    log_id="MSGW001",
                    params=[
                        f"Warning: Failed to fetch Deezer data for {name}: {str(e)}"
                    ],
                    logger_name=LOG_METHOD.APPLICATION.value,
                )
                continue

        # 4. 楽曲の取得ループ
        all_tracks_data = []
        for artist in processing_queue:
            artist_deezer_id = artist.get("deezer_id")
            if not artist_deezer_id:
                continue

            artist_tracks = []

            # A. 人気順(top_tracks)
            if pattern == "top_tracks":
                # DeezerAPI/人気曲の取得
                tracks = self.deezer_service.fetch_get_artist_top_tracks(
                    artist_deezer_id,
                    limit=track_count,
                )

                for d_track in tracks:
                    # DeezerAPI/曲の詳細情報を取得(ISRCが詳細データにしか存在しない)
                    d_track_dtl = self.deezer_service.fetch_get_track(
                        track_id=d_track["id"]
                    )
                    isrc = d_track_dtl.get("isrc")
                    if not isrc:
                        continue

                    # ISRCを基にSpotifyAPIにて検索
                    s_results = self.spotify_service.fetch_search_tracks(
                        query=f"isrc:{isrc}",
                        limit=1,
                    )

                    if s_results:
                        s_track = s_results[0]
                        popularity = s_track.get("popularity")
                        album = s_track.get("album") or {}
                        artist_tracks.append(
                            artist_tracks.append(self._format_spotify_track(s_track))
                        )

            # B. 最近のセトリ(set_list)
            elif pattern == "set_list":
                # MBID取得
                mbid = artist.get("setlistfm_mbid")

                # 必要であればMusicBrainzから取り直し
                if not mbid or artist.get("need_mbid_fetch"):
                    try:
                        res = self.musicbrainz_service.get_artist_by_deezer_id(
                            deezer_id=artist_deezer_id
                        )
                        mbid = res.get("mbid")
                    except Exception:
                        continue

                # mbidが取れなかった場合はスキップ
                if not mbid:
                    continue

                # 直近のセトリデータ取得
                try:
                    song_names = self.setlist_service.get_latest_setlist_by_mbid(
                        mbid=mbid
                    )
                    for name in song_names[:track_count]:
                        query = f"track:{name} artist:{artist['name']}"
                        search_results = self.spotify_service.fetch_search_tracks(
                            query, limit=1
                        )
                        if search_results:
                            artist_tracks.append(
                                self._format_spotify_track(search_results[0])
                            )
                except Exception as e:
                    continue

            # アーティストごとの曲を追加
            all_tracks_data.extend(artist_tracks)

        return all_tracks_data

    # トラック検索※SpotifyAPI使用
    def search_tracks(
        self,
        date_now: datetime,
        kino_id: str,
        user: M_User,
        validated_data: dict,
    ) -> List[dict]:
        """
        アーティスト名(任意)と曲名キーワードでSpotifyから楽曲を検索する。
        """
        # フロントエンドから「アーティスト名」と「曲名（キーワード）」をテキストで受け取る想定
        search_artist_name = validated_data.get("search_artist_name", "")
        search_track_name = validated_data.get("search_track_name", "")
        limit = validated_data.get("limit", 1)

        # 1. 検索クエリの構築
        if search_artist_name and search_track_name:
            # 両方ある場合は精度重視で検索
            spotify_query = f"track:{search_track_name} artist:{search_artist_name}"
        elif search_track_name:
            # 曲名のみ検索
            spotify_query = f"track:{search_track_name}"
        elif search_artist_name:
            # アーティスト名のみ検索
            spotify_query = f"artist:{search_artist_name}"
        else:
            return []

        # 2. Spotify検索実行
        search_results = self.spotify_service.fetch_search_tracks(
            query=spotify_query,
            limit=limit,
        )

        # 3. レスポンス形式の整形
        formatted_tracks = []
        for track in search_results:
            popularity = track.get("popularity")
            album = track.get("album") or {}
            formatted_tracks.append(
                {
                    "spotify_id": track.get("id"),
                    "spotify_name": track.get("name"),
                    "spotify_isrc": track.get("external_ids", {}).get("isrc"),
                    "spotify_artist_name": track.get("artists", [{}])[0].get("name"),
                    "spotify_popularity": popularity if popularity is not None else 0,
                    "spotify_duration_ms": track.get("duration_ms"),
                    "spotify_album_type": album.get("album_type"),
                    "spotify_album_id": album.get("id"),
                    "spotify_album_name": album.get("name"),
                    "spotify_release_date": album.get("release_date"),
                }
            )

        return formatted_tracks
