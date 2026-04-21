from datetime import datetime

from django.utils import timezone

# --- アカウントモジュール ---
from apps.account.models import M_User
from apps.artist.exceptions import ArtistAlreadyExistsError, ArtistNotFoundError

# --- アーティストモジュール ---
from apps.artist.models import R_ArtistTag, T_Artist

# --- 共通モジュール ---
from apps.common.models import T_FileResource
from apps.common.services.storage_service import StorageService
from apps.common.services.musicbrainz_service import MusicBrainzService
from apps.common.services.deezer_service import DeezerService
from apps.common.services.musicbrainz_service import MusicBrainzService

from core.exceptions.exceptions import ApplicationError


class ArtistService:
    """
    アーティスト情報の登録・更新・管理を行うサービスクラス
    """

    def __init__(self):
        self.deezer_service = DeezerService()
        self.storage_service = StorageService()
        self.musicbrainz_service = MusicBrainzService()

    def _update_deezer_image(
        self,
        date_now: datetime,
        kino_id: str,
        user: M_User,
        artist: T_Artist,
        latest_data,
    ):
        """Deezerの画像情報を使用してT_FileResourceを更新"""
        # Deezerの画像URLを取得 (picture_big, picture_mediumなどから選択)
        new_url = latest_data.get("picture_big") or latest_data.get("picture_medium")
        if not new_url:
            return

        # DB側の画像URLとの差分があれば更新
        if not artist.deezer_image or artist.deezer_image.external_url != new_url:
            new_image = T_FileResource.objects.create(
                file_type=T_FileResource.FileType.IMAGE,
                external_url=new_url,
                file_name=f"deezer_{artist.name}_refreshed_{timezone.now().strftime('%Y%m%d')}",
                created_by=user,
                created_method=kino_id,
                updated_by=user,
                updated_method=kino_id,
            )
            artist.deezer_image = new_image

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
        ).select_related("deezer_image", "context")

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
            # select_related: 1対1, 多対1(画像, コンテキスト)
            # prefetch_related: 多対多(タグ)
            artist = (
                T_Artist.objects.filter(
                    id=artist_id, user=user, deleted_at__isnull=True
                )
                .select_related("deezer_image", "context")
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
        self, 
        date_now: datetime, 
        kino_id: str, 
        user: M_User, 
        validated_data,
    ):
        """アーティストを新規登録する"""
        # 1. 重複チェック(論理削除されていない同一DeezerIDがないか)
        if T_Artist.objects.filter(
            user=user,
            deezer_id=validated_data["deezer_id"],
            deleted_at__isnull=True,
        ).exists():
            raise ArtistAlreadyExistsError()

        # 関連マスタの存在チェック
        # ※コンテキスト、タグに関してはシリアライザ(PrimaryKeyRelatedField)にて存在チェック済みのため不要

        # 2. 画像リソース(T_FileResource)の作成
        deezer_image = None
        if validated_data.get("image_url"):
            deezer_image = T_FileResource.objects.create(
                file_type=T_FileResource.FileType.IMAGE,
                external_url=validated_data["image_url"],
                file_name=f"deezer_{validated_data['name']}_image",
                created_by=user,
                created_method=kino_id,
                updated_by=user,
                updated_method=kino_id,
            )
        
        # 3. MBIDの登録(未設定の場合は取得し登録する)
        # ※検索時にもMBIDを返すので、自動設定は基本使わない予定(検索でのMBID大量取得が重ければこちらを検討)
        mbid = None
        is_mbid_autoset = True
        if validated_data.get("setlistfm_mbid") and validated_data.get("is_mbid_autoset") is not None:
            mbid = validated_data.get("setlistfm_mbid")
            is_mbid_autoset = validated_data.get("is_mbid_autoset", False)
        else:
            # MBIDの取得(※MusicBrainzAPIを使用)
            try:
                result: dict = self.musicbrainz_service.get_artist_by_deezer_id(
                    deezer_id=validated_data["deezer_id"],
                )
                mbid = result.get("mbid")
            except ApplicationError as e:
                # MBIDが取得できなかった場合は、is_mbid_autoset=Falseとする
                mbid = None
                is_mbid_autoset = False

        # 4. アーティスト本体の作成
        artist = T_Artist.objects.create(
            user=user,
            deezer_id=validated_data["deezer_id"],
            name=validated_data["name"],
            deezer_image=deezer_image,
            setlistfm_mbid=mbid,
            is_mbid_autoset=is_mbid_autoset,
            # validated_data['context_id'] は既にモデルインスタンスになっている
            context=validated_data.get("context_id"),
            genres=validated_data.get("genres", []),
            created_by=user,
            created_method=kino_id,
            updated_by=user,
            updated_method=kino_id,
        )

        # 5. タグの紐付け(中間テーブルR_ArtistTagの作成)
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
        self, 
        date_now: datetime, 
        kino_id: str, 
        user: M_User, 
        artist_id,
        validated_data,
    ):
        """アーティストを新規登録する"""
        # 1. 対象の取得（存在チェック）
        try:
            artist: T_Artist = T_Artist.objects.select_for_update().get(
                id=artist_id, user=user, deleted_at__isnull=True
            )
        except T_Artist.DoesNotExist:
            raise ArtistNotFoundError()

        # 2. Deezer画像URLの更新(通常送られてくる想定はないが、変えれるように入れておく)
        if "deezer_image_url" in validated_data:
            new_url = validated_data["deezer_image_url"]
            
            # 現在の画像URLと異なる場合のみ更新処理を行う
            # (artist.deezer_image が T_FileResource インスタンスである前提)
            current_image = artist.deezer_image
            
            # URLが変わっている、もしくは現在画像がない場合
            if not current_image or current_image.url != new_url:
                # --- A. 既存レコードを論理削除 ---
                if current_image:
                    current_image.deleted_at = date_now
                    current_image.updated_by = user
                    current_image.updated_method = kino_id
                    current_image.save()

                # --- B. 新しいURLでレコードを作成 ---
                # T_FileResourceに url というフィールドがある想定です
                new_image_rec = T_FileResource.objects.create(
                    file_type=T_FileResource.FileType.IMAGE,
                    url=new_url,  # ここにDeezerのURLを保存
                    file_name=f"deezer_{artist.name}_image",
                    created_by=user,
                    created_method=kino_id,
                    updated_by=user,
                    updated_method=kino_id,
                )
                
                # アーティストに紐付け
                artist.deezer_image = new_image_rec

        # 3. その他のフィールド更新
        if "setlistfm_mbid" in validated_data:
            artist.setlistfm_mbid = validated_data["setlistfm_mbid"]

        if "context_id" in validated_data:
            artist.context = validated_data["context_id"]

        artist.updated_method = kino_id
        artist.updated_by = user
        artist.save()

        # 4. タグの更新(洗替方式)
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

        # 2. 紐付いている画像の論理削除
        # deezer_image(ForeignKey)が存在する場合、そのレコードも論理削除する
        if artist.deezer_image:
            image_res = artist.deezer_image
            image_res.updated_by = user
            image_res.updated_method = kino_id
            image_res.deleted_at = date_now
            image_res.save()

        # 3. アーティスト本体の論理削除処理
        # deleted_at を入れることで、以降のfilter(deleted_at__isnull=True)から除外される
        artist.updated_by = user
        artist.updated_method = kino_id
        artist.deleted_at = date_now
        artist.save()

        # 4. タグの更新(中間テーブルは物理削除)
        # カスケード削除されない中間テーブルのレコードを掃除
        R_ArtistTag.objects.filter(artist=artist).delete()

    # ------------------------------------------------------------------
    # その他サービス
    # ------------------------------------------------------------------
    # アーティスト情報最新化(要: artist_instance)※DeezerAPI使用
    def refresh_artist(
        self, date_now: datetime, kino_id: str, user: M_User, artist_instance: T_Artist
    ):
        """
        特定のアーティスト1件をDeezerの最新情報と同期する
        """
        """Deezerの最新情報と同期"""
        latest_data = self.deezer_service.fetch_get_artist(artist_instance.deezer_id)

        # 2. 基本情報の更新
        artist_instance.name = latest_data.get("name", artist_instance.name)
        # Deezerはgenresを直接持たないことが多いが、データ構造に合わせて取得
        # artist_instance.genres = latest_data.get("genres", [])

        # 3. 前回画像と比較し、必要あれば最新化
        self._update_deezer_image(
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

    # アーティスト情報最新化(要: artist_queryset)※DeezerAPI使用
    def refresh_artists(
        self, date_now: datetime, kino_id: str, user: M_User, artist_queryset
    ):
        """
        QuerySetを受け取り、その中の全アーティストをDeezerの最新情報と同期する
        """
        deezer_ids = [a.deezer_id for a in artist_queryset]

        # 1. Deezerから一括取得
        # ※エラーはDeezerService側から投げられるものを使用
        latest_data_list = self.deezer_service.fetch_get_artists(deezer_ids)

        # 2. データをマッピング(DeezerIDをキーにした辞書にすると更新が楽)
        latest_map = {data["id"]: data for data in latest_data_list}

        # 3. 更新処理
        updated_artists = []
        for artist in artist_queryset:
            data = latest_map.get(artist.deezer_id)
            if not data:
                continue

            # ここで1件更新のロジック(get_refreshed_artistの内容)を再利用
            # 大量更新の場合は、画像URLの変更チェックなどを効率化
            artist.name = data.get("name", artist.name)
            # Deezerはgenresを直接持たないことが多いが、データ構造に合わせて取得
            # artist.genres = data.get("genres", [])

            # 前回画像と比較し、必要あれば最新化
            self._update_deezer_image(
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

    # アーティスト検索※DeezerAPI使用
    def search_artist(self, date_now: datetime, kino_id: str, user: M_User, validated_data):
        """
        DeezerAPIでアーティストを検索し、自社DBの登録状況を付与して返す
        """
        # フロントエンドから検索パラメータで受け取る想定
        query = validated_data.get("q")
        limit = validated_data.get("limit", 10)
        include_mbid = validated_data.get("include_mbid", False)

        # 1. DeezerService(認証済み)を使用して検索実行
        deezer_raw_list = self.deezer_service.fetch_search_artists(
            query=query, 
            limit=limit,
        )
        if not deezer_raw_list:
            return []

        # IDの抽出と文字列化(ループ内でのstr()変換を減らす)
        deezer_id_map = {str(item["id"]): item for item in deezer_raw_list}
        deezer_ids = list(deezer_id_map.keys())

        # 3. アーティストID/MBIDを一括取得
        registered_data = T_Artist.objects.filter(
            user=user,
            deezer_id__in=deezer_ids,
            deleted_at__isnull=True,
        ).values("deezer_id", "setlistfm_mbid")

        # 検索用に辞書化: { "deezer_id": "setlistfm_mbid" }
        registered_map = {str(item["deezer_id"]): item["setlistfm_mbid"] for item in registered_data}

        # 3. MBID取得(必要な場合のみ)
        external_mbid_map = {}
        if include_mbid:
            for d_id in deezer_ids:
                # 登録済みならDBのsetlistfm_mbidがあるため、外部APIは呼ばない
                if d_id not in registered_map:
                    try:
                        result = self.musicbrainz_service.get_artist_by_deezer_id(deezer_id=d_id)
                        external_mbid_map[d_id] = result.get("mbid")
                    except ApplicationError:
                        external_mbid_map[d_id] = None

        # 4. 生データに「is_registered」フラグ「mbid」をマージして整形
        formatted_results = []
        for d_id, item in deezer_id_map.items():
            is_registered = d_id in registered_map
            formatted_results.append({
                "deezer_id": d_id,
                "name": item["name"],
                # 画像URLの階層をフロントが扱いやすいようにフラットにする
                "image_url": item.get("picture_big"),
                # "genres": item.get("genres", []),
                # "popularity": item.get("popularity"),
                "is_registered": is_registered,
                "mbid": registered_map.get(d_id) if is_registered else external_mbid_map.get(d_id),
                # T_Artistのフィールドをそのまま返却未登録の場合はNone)
                "setlistfm_mbid": registered_map.get(d_id) if is_registered else None,
            })

        return formatted_results