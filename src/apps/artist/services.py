from collections import defaultdict
from datetime import datetime

from django.utils import timezone

# --- アカウントモジュール ---
from apps.account.models import M_User
from apps.artist.exceptions import ArtistAlreadyExistsError, ArtistNotFoundError

# --- アーティストモジュール ---
from apps.artist.models import R_ArtistTag, T_Artist

# --- 共通モジュール ---
from apps.common.models import T_FileResource
from apps.common.services.deezer_service import DeezerService
from apps.common.services.musicbrainz_service import MusicBrainzService
from apps.common.services.spotify_service import SpotifyService
from apps.common.services.lastfm_service import LastfmService
from apps.common.services.storage_service import StorageService
from core.consts import LOG_METHOD
from core.exceptions.exceptions import ApplicationError
from core.utils.log_helpers import log_output_by_msg_id


class ArtistService:
    """
    アーティスト情報の登録/更新/管理を行うサービスクラス
    """

    def __init__(self):
        self.spotify_service = SpotifyService()
        self.deezer_service = DeezerService()
        self.lastfm_service = LastfmService()
        self.storage_service = StorageService()
        self.musicbrainz_service = MusicBrainzService()

    def _update_external_icon(
        self,
        date_now: datetime,
        kino_id: str,
        user: M_User,
        artist: T_Artist,
        latest_data,
    ):
        """Spotifyの画像情報を使用してT_FileResourceを更新"""
        # Spotifyの画像配列からURLを取得(通常 images[0] が最大サイズ)
        images = latest_data.get("images", [])
        new_url = images[0]["url"] if images else None

        if not new_url:
            return

        # DB側の画像URLとの差分があれば更新
        if not artist.spotify_image or artist.spotify_image.url != new_url:
            # 既存画像があれば論理削除
            if artist.spotify_image:
                artist.spotify_image.deleted_at = date_now
                artist.spotify_image.save()

            new_image = T_FileResource.objects.create(
                file_type=T_FileResource.FileType.IMAGE,
                url=new_url,
                file_name=f"spotify_{artist.name}_image_{date_now.strftime('%Y%m%d')}",
                created_by=user,
                created_method=kino_id,
                updated_by=user,
                updated_method=kino_id,
            )
            artist.spotify_image = new_image

    def _link_external_ids(
        self, 
        name: str, 
        spotify_id: str
    ):
        """
        名前とSpotifyIDから、DeezerIDとMusicBrainzID(MBID)を取得/名寄せする
        """
        deezer_id = None
        is_deezer_autoset = False
        mbid = None
        is_mbid_autoset = False
        lastfm_name = None

        # 1. MBIDの取得
        try:
            result = self.musicbrainz_service.get_artist_by_spotify_id(spotify_id=spotify_id)
            if result and result.get("mbid"):
                mbid = result.get("mbid")
                is_mbid_autoset = True
        except ApplicationError as e:
            log_output_by_msg_id(
                log_id="MSGW001",
                params=[f"Warning: Failed to fetch MBID for {name}: {str(e)}"],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
        except Exception:
            pass

        # 2. DeezerIDの取得
        try:
            results = self.deezer_service.fetch_search_artists(query=name, limit=1)
            if results and len(results) > 0:
                deezer_id = str(results[0].get("id"))
                is_deezer_autoset = True
        except ApplicationError as e:
            log_output_by_msg_id(
                log_id="MSGW001",
                params=[f"Warning: Failed to fetch Deezer ID for {name}: {str(e)}"],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
        except Exception:
            pass
        
        # 3. LastFM側を検索し正式名称を取得
        try:
            lastfm_name = self.lastfm_service.get_canonical_artist_name(artist_name=name)
        except ApplicationError as e:
            log_output_by_msg_id(
                log_id="MSGW001",
                params=[f"Warning: Failed to fetch LastFM name for {name}: {str(e)}"],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
        except Exception:
            pass

        return {
            "mbid": mbid,
            "is_mbid_autoset": is_mbid_autoset,
            "deezer_id": deezer_id,
            "is_deezer_autoset": is_deezer_autoset,
            "lastfm_name": lastfm_name,
        }

    # ------------------------------------------------------------------
    # 一覧取得系サービス
    # ------------------------------------------------------------------
    # アーティスト一覧取得
    def list_artist(
        self, 
        date_now: datetime, 
        kino_id: str, 
        user: M_User, 
        name=None, 
        tag_ids=None,
    ):
        """
        フィルタリングを考慮したアーティスト一覧取得
        """
        # 1. 基本クエリ(自分かつ未削除 + N+1対策)
        queryset = T_Artist.objects.filter(
            user=user, deleted_at__isnull=True
        ).select_related("external_icon", "context")

        # 2. 名前フィルター (部分一致)
        if name:
            queryset = queryset.filter(name__icontains=name)

        # 3. タグフィルター (複数指定可、OR条件)
        if tag_ids:
            # tag_idsはリスト [uuid, uuid] を想定
            queryset = queryset.filter(tags__id__in=tag_ids).distinct()

        # 4. ソート
        return queryset.order_by("-created_at")

    # 関連アーティスト一覧取得
    def list_related_artist(
        self,
        date_now: datetime,
        kino_id: str,
        user: M_User,
        validated_data,
    ):
        """
        関連するアーティスト一覧取得
        """
        _lastfm_related_limit = 10
        get_related_artists_count = validated_data.get("get_related_artists_count", 5)
        # 1. 基本クエリ(自分かつ未削除)
        recent_artists = (
            T_Artist.objects.filter(user=user, deleted_at__isnull=True)
            .order_by("-created_at")
            .values("spotify_name", "lastfm_name")[:10]
        )
        old_artists = (
            T_Artist.objects.filter(user=user, deleted_at__isnull=True)
            .order_by("created_at")
            .values("spotify_name", "lastfm_name")[:10]
        )

        original_favorites = {
            f["spotify_name"]: f for f in list(recent_artists) + list(old_artists)
        }
        original_artists = list(original_favorites.values())

        # 関連アーティストの集計用
        # キー: アーティスト名, 値  : スコア合計
        related_artist_scores = defaultdict(float)
        # 既存のアーティスト名のリスト(除外用)
        original_names = {a["spotify_name"] for a in original_artists}

        # 2. 関連アーティストの算出
        for artist in original_artists:
            try:
                artist_name = artist["spotify_name"]
                # 1. LastFM側を検索し正式名称を取得
                l_artist_name = self.lastfm_service.get_canonical_artist_name(
                    artist_name
                )
                if not l_artist_name:
                    continue

                # 関連アーティストを取得
                # Last.fm APIの"match"フィールドを利用
                l_artists = self.lastfm_service.get_similar_artists(
                    l_artist_name, limit=_lastfm_related_limit
                )

                for l_artist in l_artists:
                    # 既に選択されているアーティストは関連として追加しない
                    if l_artist["name"] in original_names:
                        continue

                    # スコアを加算 (Last.fmの match は文字列の数値なのでfloatに変換)
                    score = float(l_artist.get("match", 0))
                    related_artist_scores[l_artist["name"]] += score

            except Exception as e:
                # ここでログを出して、失敗したアーティストはスキップし、次の処理へ継続
                log_output_by_msg_id(
                    log_id="MSGW001",
                    params=[
                        f"Warning: Failed to fetch related artists for {artist['name']}: {str(e)}"
                    ],
                    logger_name=LOG_METHOD.APPLICATION.value,
                )
                continue

        # 3. スコアでソートして関連アーティストの上位を抽出
        # items = [("アーティスト名", スコア), ...]
        sorted_related = sorted(
            related_artist_scores.items(), key=lambda x: x[1], reverse=True
        )
        top_related = sorted_related[:get_related_artists_count]

        spotify_raw_list = []
        # 4. 上位の関連アーティストをSpotifyで検索し追加
        for name, score in top_related:
            try:
                # Spotifyで検索してIDを取得
                spotify_results = self.spotify_service.fetch_search_artists(
                    query=name, limit=1
                )
                if not spotify_results:
                    continue

                spotify_raw_list.append(spotify_results[0])

            except Exception as e:
                # 検索失敗時も、他のアーティスト処理を止めない
                log_output_by_msg_id(
                    log_id="MSGW001",
                    params=[
                        f"Warning: Failed to fetch Spotify data for {name}: {str(e)}"
                    ],
                    logger_name=LOG_METHOD.APPLICATION.value,
                )
                continue

        # IDの抽出と文字列化
        spotify_id_map = {str(item["id"]): item for item in spotify_raw_list}
        spotify_ids = list(spotify_id_map.keys())

        # 5. 自社DB登録状況の確認
        registered_ids = set(
            T_Artist.objects.filter(
                user=user,
                spotify_id__in=spotify_ids,
                deleted_at__isnull=True,
            ).values_list("spotify_id", flat=True)
        )

        # 6. データの整形
        formatted_results = []
        for s_id, item in spotify_id_map.items():
            images = item.get("images", [])
            icon_url = images[0]["url"] if images else None

            formatted_results.append(
                {
                    "spotify_id": s_id,
                    "spotify_name": item["name"],
                    "icon_url": icon_url,
                    "is_registered": s_id in registered_ids,
                }
            )

        return formatted_results

    # ------------------------------------------------------------------
    # 詳細取得系サービス
    # ------------------------------------------------------------------
    # アーティスト詳細取得
    def detail_artist(
        self, 
        date_now: datetime, 
        kino_id: str, 
        user: M_User, 
        artist_id
    ):
        """
        特定のアーティスト詳細を取得する(N+1対策済)
        """
        try:
            # select_related: 1対1, 多対1(画像, コンテキスト)
            # prefetch_related: 多対多(タグ)
            artist = (
                T_Artist.objects.filter(
                    id=artist_id, user=user, deleted_at__isnull=True
                )
                .select_related("external_icon", "context")
                .prefetch_related("tags")
                .get()
            )

            return artist

        except T_Artist.DoesNotExist:
            raise ArtistNotFoundError()

    # ------------------------------------------------------------------
    # 登録系サービス
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
        # 1. 重複チェック(論理削除されていない同一SpotifyIDがないか)
        if T_Artist.objects.filter(
            user=user,
            spotify_id=validated_data["spotify_id"],
            deleted_at__isnull=True,
        ).exists():
            raise ArtistAlreadyExistsError()

        # 関連マスタの存在チェック
        # ※コンテキスト、タグに関してはシリアライザ(PrimaryKeyRelatedField)にて存在チェック済みのため不要

        # 2. 画像リソース(T_FileResource)の作成
        spotify_image = None
        if validated_data.get("icon_url"):
            spotify_image = T_FileResource.objects.create(
                file_type=T_FileResource.FileType.IMAGE,
                external_url=validated_data["icon_url"],
                file_name=f"spotify_{validated_data['spotify_name']}_image_{date_now.strftime('%Y%m%d')}",
                created_by=user,
                created_method=kino_id,
                updated_by=user,
                updated_method=kino_id,
            )

        # 3. 外部ID(MBID/DeezerID)の取得処理(名寄せ)
        linked_ids = self._link_external_ids(
            name=validated_data["spotify_name"],
            spotify_id=validated_data["spotify_id"]
        )

        # 4. アーティスト本体の作成
        artist = T_Artist.objects.create(
            user=user,
            spotify_id=validated_data["spotify_id"],
            spotify_name=validated_data["spotify_name"],
            display_name=validated_data["display_name"],
            external_icon=spotify_image,
            deezer_id=linked_ids["deezer_id"],
            is_deezer_autoset=linked_ids["is_deezer_autoset"],
            # lastfmの取得はパフォーマンスと要調整(取得をコメントアウト)したいので、「.get()」で最悪Noneで登録させる
            lastfm_name=linked_ids.get("lastfm_name"),
            mbid=linked_ids["mbid"],
            is_mbid_autoset=linked_ids["is_mbid_autoset"],
            # validated_data['context_id'] は既にモデルインスタンスになっている
            context=validated_data.get("context_id"),
            created_by=user,
            created_method=kino_id,
            updated_by=user,
            updated_method=kino_id,
        )

        # 5. タグの紐付け(中間テーブルR_ArtistTagの作成)
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
    # 更新系サービス
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
        # 1. 対象の取得(存在チェック)
        try:
            artist: T_Artist = T_Artist.objects.select_for_update().get(
                id=artist_id, user=user, deleted_at__isnull=True
            )
        except T_Artist.DoesNotExist:
            raise ArtistNotFoundError()

        # 2. その他のフィールド更新 
        if "mbid" in validated_data:
            artist.mbid = validated_data["mbid"]
            artist.is_mbid_autoset = False
        
        if "deezer_id" in validated_data:
            artist.deezer_id = validated_data["deezer_id"]
            artist.is_deezer_autoset = False

        if "context_id" in validated_data:
            artist.context = validated_data["context_id"]

        artist.updated_method = kino_id
        artist.updated_by = user
        artist.save()

        # 3. タグの更新(洗替方式)
        if "tag_ids" in validated_data:  # validated_dataに含まれているときのみ更新
            # 既存の紐付けを物理削除(中間テーブルなので物理削除)
            R_ArtistTag.objects.filter(artist=artist).delete()

            # 新しいタグを登録
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
    # 削除系サービス
    # ------------------------------------------------------------------
    # アーティスト削除
    def delete_artist(
        self, 
        date_now: datetime, 
        kino_id: str, 
        user: M_User, 
        artist_id
    ):
        """アーティストを論理削除する"""
        # 1. 対象の取得
        # 自分のデータ かつ すでに削除されていないものを対象にする
        try:
            artist: T_Artist = T_Artist.objects.select_for_update().get(
                id=artist_id, user=user, deleted_at__isnull=True
            )
        except T_Artist.DoesNotExist:
            raise ArtistNotFoundError()

        # 2. 紐付いている画像の論理削除
        # external_icon(ForeignKey)が存在する場合、そのレコードも論理削除する
        if artist.external_icon:
            image_res = artist.external_icon
            image_res.updated_by = user
            image_res.updated_method = kino_id
            image_res.deleted_at = date_now
            image_res.save()

        # 3. アーティスト本体の論理削除処理
        # deleted_at を入れることで、以降のfilter(deleted_at__isnull=True)から除外される
        artist.updated_by = user
        artist.updated_method = kino_id
        artist.deleted_at = date_now
        artist.save()

        # 4. タグの更新(中間テーブルは物理削除)
        # カスケード削除されない中間テーブルのレコードを掃除
        R_ArtistTag.objects.filter(artist=artist).delete()

    # ------------------------------------------------------------------
    # その他サービス
    # ------------------------------------------------------------------
    # アーティスト情報最新化(要: artist_instance)※SpotifyAPI使用
    def refresh_artist(
        self, 
        date_now: datetime, 
        kino_id: str, 
        user: M_User, 
        artist_instance: T_Artist,
    ):
        """
        特定のアーティスト1件をSpotifyの最新情報と同期する
        """
        if not artist_instance.spotify_id:
            return artist_instance

        # 1. Spotifyの最新情報と同期
        latest_data = self.spotify_service.fetch_get_artist(artist_instance.spotify_id)

        # 2. 基本情報の更新
        artist_instance.spotify_name = latest_data.get("name", artist_instance.spotify_name)

        # 3. 前回画像と比較し、必要あれば最新化
        self._update_external_icon(
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
        self, 
        date_now: datetime, 
        kino_id: str, 
        user: M_User, 
        artist_queryset,
    ):
        """
        QuerySetを受け取り、その中の全アーティストをSpotifyの最新情報と同期する
        """
        spotify_ids = [a.spotify_id for a in artist_queryset if a.spotify_id]
        if not spotify_ids:
            return list(artist_queryset)

        # 1. Spotifyから一括取得
        # ※エラーはSpotifyService側から投げられるものを使用
        latest_data_list = self.spotify_service.fetch_get_artists(spotify_ids)

        # 2. データをマッピング(SpotifyIDをキーにした辞書にすると更新が楽)
        latest_map = {data["id"]: data for data in latest_data_list}

        # 3. 更新処理
        updated_artists = []
        for artist in artist_queryset:
            data = latest_map.get(artist.spotify_id)
            if not data:
                continue

            # ここで1件更新のロジック(get_refreshed_artistの内容)を再利用
            # 大量更新の場合は、画像URLの変更チェックなどを効率化
            artist.spotify_name = data.get("name", artist.spotify_name)

            # 前回画像と比較し、必要あれば最新化
            self._update_external_icon(
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
    def search_artists(
        self, 
        date_now: datetime, 
        kino_id: str, 
        user: M_User, 
        validated_data,
    ):
        """
        SpotifyAPIでアーティストを検索し、登録状況を付与して返す
        """
        query = validated_data.get("q")
        limit = validated_data.get("limit", 10)

        # 1. SpotifyServiceを使用して検索実行
        spotify_raw_list = self.spotify_service.fetch_search_artists(
            query=query,
            limit=limit,
        )
        if not spotify_raw_list:
            return []

        # 2. SpotifyIDの一覧を抽出
        spotify_ids = [str(item["id"]) for item in spotify_raw_list]

        # 3. 自社DBに既に登録されているIDをセットで取得
        registered_ids = set(
            T_Artist.objects.filter(
                user=user,
                spotify_id__in=spotify_ids,
                deleted_at__isnull=True,
            ).values_list("spotify_id", flat=True)
        )

        # 4. MusicBrainzから日本語名(display_name)を一括検索・特定してマッピング
        # (URL検索はヒットしづらいため、名前・エイリアスのOR検索で候補を一括取得する)
        mb_name_map = {}
        if spotify_raw_list:
            # クエリの構築: artist:"名前" OR alias:"名前"
            query_parts = []
            for item in spotify_raw_list:
                clean_name = item["name"].replace('"', '\\"').replace(':', '\\:')
                query_parts.append(f'artist:"{clean_name}" OR alias:"{clean_name}"')
            
            mb_query = " OR ".join(query_parts)
            try:
                # 名前ベースのOR検索を実行 (1リクエストで複数候補をさらってくる)
                mb_search_results = self.musicbrainz_service.fetch_search_artists(mb_query, limit=20)
                artists = mb_search_results.get("artists", [])
                
                # 名前またはエイリアスによるマッピング
                for mb_artist in artists:
                    # ===================================================================================================
                    # MEMO: 効率が悪いので、日本のアーティストだけを対象にする(中国等の対応をする場合はレス速度を犠牲にするか改善が必要)
                    # ===================================================================================================
                    if mb_artist.get("country") != "JP":
                        continue
                    mb_name = mb_artist.get("name")
                    mb_aliases = [a.get("name").lower() for a in mb_artist.get("aliases", [])]
                    
                    # 候補をSpotify側の名前に紐付ける(大小文字無視)
                    for item in spotify_raw_list:
                        s_name = item["name"].lower()
                        # --- 誤認防止のロジック ---
                        # 1. MusicBrainzのメイン名とが完全一致する場合を最優先
                        if s_name == mb_name.lower():
                            mb_name_map[item["id"]] = mb_name
                        # 2. メイン名が一致しないが、エイリアスに含まれる場合 (まだ埋まっていない場合のみ)
                        elif s_name in mb_aliases:
                            if item["id"] not in mb_name_map:
                                mb_name_map[item["id"]] = mb_name
            except Exception:
                pass

        # 5. データの整形
        formatted_results = []
        for item in spotify_raw_list:
            s_id = str(item["id"])
            s_name = item["name"]

            # Spotifyの画像配列からURLを取得(一番大きいサイズを想定)
            images = item.get("images", [])
            icon_url = images[0]["url"] if images else None

            # --- display_name の決定 ---
            # 1. まずバルク検索でヒットした MusicBrainz の正名を採用
            display_name = mb_name_map.get(item["id"])
            
            # ===================================================================================================
            # 2. ヒットしなかった場合は、個別にSpotifyID経由で解決(キャッシュを期待)
            # ※日本以外も全て取得する場合は下記や上部の一括取得後のcountry="JP"のチェックを外す
            # ===================================================================================================
            # if not display_name:
            #     try:
            #         mb_result = self.musicbrainz_service.get_artist_by_spotify_id(s_id)
            #         if mb_result and mb_result.get("name"):
            #             display_name = mb_result.get("name")
            #     except Exception:
            #         pass
            
            # どれもダメならSpotifyの名前をそのまま使用
            if not display_name:
                display_name = s_name

            formatted_results.append(
                {
                    "spotify_id": s_id,
                    "spotify_name": s_name,
                    "display_name": display_name,
                    "icon_url": icon_url,
                    "is_registered": s_id in registered_ids,
                }
            )

        return formatted_results