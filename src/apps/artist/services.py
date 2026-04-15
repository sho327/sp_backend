from datetime import datetime

from django.utils import timezone

# --- アカウントモジュール ---
from apps.account.models import M_User
from apps.artist.exceptions import ArtistAlreadyExistsError, ArtistNotFoundError

# --- アーティストモジュール ---
from apps.artist.models import R_ArtistTag, T_Artist

# --- 共通モジュール ---
from apps.common.models import T_FileResource
from apps.common.services.spotify_service import SpotifyService
from apps.common.services.storage_service import StorageService


class ArtistService:
    """
    アーティスト情報の登録・更新・管理を行うサービスクラス
    """

    def __init__(self):
        self.spotify_service = SpotifyService()
        self.storage_service = StorageService()

    def _update_spotify_image(
        self,
        date_now: datetime,
        kino_id: str,
        user: M_User,
        artist: T_Artist,
        latest_data,
    ):
        """画像URLの比較とT_FileResourceの作成/紐付けを行う共通ロジック"""
        images = latest_data.get("images", [])
        if not images:
            return

        new_url = images[0]["url"]
        # DB側の画像URLとの差分があれば更新
        if not artist.spotify_image or artist.spotify_image.external_url != new_url:
            new_image = T_FileResource.objects.create(
                file_type=T_FileResource.FileType.IMAGE,
                external_url=new_url,
                file_name=f"spotify_{artist.name}_refreshed_{timezone.now().strftime('%Y%m%d')}",
                created_by=user,
                created_method=kino_id,
                updated_by=user,
                updated_method=kino_id,
            )
            artist.spotify_image = new_image

    # ------------------------------------------------------------------
    # 一覧取得系サービス
    # ------------------------------------------------------------------
    # アーティスト一覧取得
    def list_artist(
        self, date_now: datetime, kino_id: str, user: M_User, name=None, tag_ids=None
    ):
        """
        フィルタリングを考慮したアーティスト一覧取得
        """
        # 1. 基本クエリ（自分かつ未削除 ＋ N+1対策）
        queryset = T_Artist.objects.filter(
            user=user, deleted_at__isnull=True
        ).select_related("spotify_image", "context")

        # 2. 名前フィルター (部分一致)
        if name:
            queryset = queryset.filter(name__icontains=name)

        # 3. タグフィルター (複数指定可、OR条件)
        if tag_ids:
            # tag_idsはリスト [uuid, uuid] を想定
            queryset = queryset.filter(tags__id__in=tag_ids).distinct()

        # 4. ソート
        queryset = queryset.order_by("-created_at")

        return queryset

    # ------------------------------------------------------------------
    # 詳細取得系サービス
    # ------------------------------------------------------------------
    # アーティスト詳細取得
    def detail_artist(self, date_now: datetime, kino_id: str, user: M_User, artist_id):
        """
        特定のアーティスト詳細を取得する(N+1対策済)
        """
        try:
            # select_related: 1対1, 多対1 (画像, コンテキスト)
            # prefetch_related: 多対多 (タグ)
            artist = (
                T_Artist.objects.filter(
                    id=artist_id, user=user, deleted_at__isnull=True
                )
                .select_related("spotify_image", "context")
                .prefetch_related("tags")  # 以前作ったタグ一覧も一括取得
                .get()
            )

            return artist

        except T_Artist.DoesNotExist:
            raise ArtistNotFoundError()

    # ------------------------------------------------------------------
    # 登録系サービス
    # ------------------------------------------------------------------
    # アーティスト登録
    def create_artist(
        self, date_now: datetime, kino_id: str, user: M_User, validated_data
    ):
        """アーティストを新規登録する"""
        # 1. 重複チェック(論理削除されていない同一SpotifyIDがないか)
        if T_Artist.objects.filter(
            user=user,
            spotify_id=validated_data["spotify_id"],
            deleted_at__isnull=True,
        ).exists():
            raise ArtistAlreadyExistsError()

        # 関連マスタの存在チェック
        # ※コンテキスト、タグに関してはシリアライザ(PrimaryKeyRelatedField)にて存在チェック済みのため不要

        # 2. 画像リソース(T_FileResource)の作成
        spotify_image = None
        if validated_data.get("image_url"):
            spotify_image = T_FileResource.objects.create(
                file_type=T_FileResource.FileType.IMAGE,
                external_url=validated_data["image_url"],
                file_name=f"spotify_{validated_data['name']}_image",
                created_by=user,
                created_method=kino_id,
                updated_by=user,
                updated_method=kino_id,
            )

        # 3. アーティスト本体の作成
        artist = T_Artist.objects.create(
            user=user,
            spotify_id=validated_data["spotify_id"],
            name=validated_data["name"],
            spotify_image=spotify_image,
            # validated_data['context_id'] は既にモデルインスタンスになっている
            context=validated_data.get("context_id"),
            genres=validated_data.get("genres", []),
            created_by=user,
            created_method=kino_id,
            updated_by=user,
            updated_method=kino_id,
        )

        # 4. タグの紐付け(中間テーブルR_ArtistTagの作成)
        tags = validated_data.get("tag_ids", [])
        if tags:
            tag_links = [
                R_ArtistTag(
                    artist=artist,
                    tag=tag,
                    created_by=user,
                    created_method=kino_id,
                    updated_by=user,
                    updated_method=kino_id,
                )
                for tag in tags
            ]
            R_ArtistTag.objects.bulk_create(tag_links)

        return artist

    # ------------------------------------------------------------------
    # 更新系サービス
    # ------------------------------------------------------------------
    # アーティスト更新
    def update_artist(
        self, date_now: datetime, kino_id: str, user: M_User, artist_id, validated_data
    ):
        """アーティストを新規登録する"""
        # 1. 対象の取得（存在チェック）
        try:
            artist: T_Artist = T_Artist.objects.select_for_update().get(
                id=artist_id, user=user, deleted_at__isnull=True
            )
        except T_Artist.DoesNotExist:
            raise ArtistNotFoundError()

        # 1. 画像の保存
        if "image" in validated_data:
            storage_path = self.storage_service.upload_file(
                file_data=validated_data["image"].file,
                folder_path="artists",
                original_filename=validated_data["image"].name,
            )
            self.delete_file(artist.spotify_image.storage_path)
            artist.spotify_image = T_FileResource.objects.create(
                file_type=T_FileResource.FileType.IMAGE,
                storage_path=storage_path,
                file_name=f"spotify_{validated_data['name']}_image",
                created_by=user,
                created_method=kino_id,
                updated_by=user,
                updated_method=kino_id,
            )

        # 2. コンテキストの更新
        if "context_id" in validated_data:  # validated_dataに含まれているときのみ更新
            artist.context = validated_data["context_id"]

        # 3. SetlistFmIdの更新
        if "setlistfm_id" in validated_data:  # validated_dataに含まれているときのみ更新
            artist.setlistfm_id = validated_data["setlistfm_id"]

        artist.updated_method = kino_id
        artist.updated_by = user
        artist.save()

        # 3. タグの更新(洗替方式)
        if "tag_ids" in validated_data:  # validated_dataに含まれているときのみ更新
            # 既存の紐付けを物理削除(中間テーブルなので物理削除)
            R_ArtistTag.objects.filter(artist=artist).delete()

            # 新しいタグを登録
            tags = validated_data["tag_ids"]
            if tags:
                tag_links = [
                    R_ArtistTag(
                        artist=artist,
                        tag=tag,
                        created_by=user,
                        created_method=kino_id,
                        updated_by=user,
                        updated_method=kino_id,
                    )
                    for tag in tags
                ]
                R_ArtistTag.objects.bulk_create(tag_links)

        return artist

    # ------------------------------------------------------------------
    # 削除系サービス
    # ------------------------------------------------------------------
    # アーティスト削除
    def delete_artist(elf, date_now: datetime, kino_id: str, user: M_User, artist_id):
        """アーティストを論理削除する"""
        # 1. 対象の取得
        # 自分のデータ かつ すでに削除されていないものを対象にする
        try:
            artist: T_Artist = T_Artist.objects.select_for_update().get(
                id=artist_id, user=user, deleted_at__isnull=True
            )
        except T_Artist.DoesNotExist:
            raise ArtistNotFoundError()

        # 2. 論理削除処理
        # deleted_at を入れることで、以降のfilter(deleted_at__isnull=True)から除外される
        artist.updated_by = user
        artist.updated_method = kino_id
        artist.deleted_at = date_now
        artist.save()

        # ※ 中間テーブルR_ArtistTagは、親のT_Artistが論理削除されていれば
        # 通常の一覧取得クエリには出てこなくなるため、そのままでも運用上問題無い(基本はT_Artistのフラグ管理だけでOK)
        # ※今回は気になるので既存の紐付けも物理削除(中間テーブルなので物理削除)
        R_ArtistTag.objects.filter(artist=artist).delete()

    # ------------------------------------------------------------------
    # その他サービス
    # ------------------------------------------------------------------
    # アーティスト情報最新化(要: artist_instance)※SpotifyAPI使用
    def refresh_artist(
        self, date_now: datetime, kino_id: str, user: M_User, artist_instance: T_Artist
    ):
        """
        特定のアーティスト1件をSpotifyの最新情報と同期する
        """
        # 1. Spotifyから取得
        # ※エラーはSpotifyService側から投げられるものを使用
        latest_data = self.spotify_service.fetch_get_artist(artist_instance.spotify_id)

        # 2. 基本情報の更新
        artist_instance.name = latest_data.get("name", artist_instance.name)
        artist_instance.genres = latest_data.get("genres", [])

        # 3. 前回画像と比較し、必要あれば最新化
        self._update_spotify_image(
            date_now=date_now,
            kino_id=kino_id,
            user=user,
            artist=artist_instance,
            latest_data=latest_data,
        )

        # 4. 保存
        artist_instance.updated_by = user
        artist_instance.updated_method = kino_id
        artist_instance.save()

        return artist_instance

    # アーティスト情報最新化(要: artist_queryset)※SpotifyAPI使用
    def refresh_artists(
        self, date_now: datetime, kino_id: str, user: M_User, artist_queryset
    ):
        """
        QuerySetを受け取り、その中の全アーティストをSpotifyの最新情報と同期する
        """
        spotify_ids = [a.spotify_id for a in artist_queryset]

        # 1. Spotifyから一括取得
        # ※エラーはSpotifyService側から投げられるものを使用
        latest_data_list = self.spotify_service.fetch_get_artists(spotify_ids)

        # 2. データをマッピング（SpotifyIDをキーにした辞書にすると更新が楽）
        latest_map = {data["id"]: data for data in latest_data_list}

        # 3. 更新処理
        updated_artists = []
        for artist in artist_queryset:
            data = latest_map.get(artist.spotify_id)
            if not data:
                continue

            # ここで1件更新のロジック(get_refreshed_artistの内容)を再利用
            # 大量更新の場合は、画像URLの変更チェックなどを効率化
            artist.name = data.get("name", artist.name)
            artist.genres = data.get("genres", [])

            # 前回画像と比較し、必要あれば最新化
            self._update_spotify_image(
                date_now=date_now,
                kino_id=kino_id,
                user=user,
                artist=artist,
                latest_data=data,
            )

            artist.updated_by = user
            artist.updated_method = kino_id
            artist.save()
            updated_artists.append(artist)

        return updated_artists

    # アーティスト検索※SpotifyAPI使用
    def search_artist(self, user: M_User, query, limit):
        """
        SpotifyAPIでアーティストを検索し、自社DBの登録状況を付与して返す
        """
        # 1. SpotifyService(認証済み)を使用して検索実行
        spotify_raw_list = self.spotify_service.fetch_search_artists(
            query=query, limit=limit
        )
        if not spotify_raw_list:
            return []

        # 2. 検索結果の全SpotifyIDを抽出
        spotify_ids = [item["id"] for item in spotify_raw_list]

        # 3. 自社DBに登録されている(削除されていない)アーティストIDを一括取得
        # N+1を防ぐため、一回のクエリで取得する
        registered_ids = T_Artist.objects.filter(
            user=user,  # request.userのプロファイル等、適切なユーザー判定
            spotify_id__in=spotify_ids,
            deleted_at__isnull=True,
        ).values_list("spotify_id", flat=True)

        # 4. 生データに「is_registered」フラグをマージして整形
        formatted_results = []
        for item in spotify_raw_list:
            formatted_results.append(
                {
                    "spotify_id": item["id"],
                    "name": item["name"],
                    # 画像URLの階層をフロントが扱いやすいようにフラットにする
                    "image_url": item["images"][0]["url"] if item["images"] else None,
                    "genres": item.get("genres", []),
                    "popularity": item.get("popularity"),
                    "is_registered": item["id"] in registered_ids,
                }
            )

        return formatted_results
