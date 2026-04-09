import uuid
from django.db import transaction
from django.utils import timezone
from django.db import IntegrityError

# --- コアモジュール ---
from core.services.spotify_service import SpotifyService
from core.exceptions.exceptions import ExternalServiceError
from core.consts import LOG_METHOD
from core.utils.log_helpers import log_output_by_msg_id
# --- 共通モジュール ---
from apps.common.models import T_FileResource
# --- アーティストモジュール ---
from apps.artist.models import T_Artist, R_ArtistTag
from apps.artist.exceptions import ArtistAlreadyExistsError, SpotifyLinkageError


class ArtistService:
    """
    アーティスト情報の登録・更新・管理を行うサービスクラス
    """
    def __init__(self):
        self.spotify_service = SpotifyService()
    
    def _update_spotify_image(self, artist, latest_data, kino_id):
        """画像URLの比較とT_FileResourceの作成・紐付けを行う共通ロジック"""
        images = latest_data.get('images', [])
        if not images:
            return

        new_url = images[0]['url']
        if not artist.spotify_image or artist.spotify_image.external_url != new_url:
            from apps.common.models import T_FileResource
            new_image = T_FileResource.objects.create(
                file_type=T_FileResource.FileType.IMAGE,
                external_url=new_url,
                file_name=f"spotify_{artist.name}_refreshed_{timezone.now().strftime('%Y%m%d')}",
                created_by_id=artist.user_id,
                created_method=kino_id,
                updated_by_id=artist.user_id,
                updated_method=kino_id,
            )
            artist.spotify_image = new_image
    
    def get_refreshed_artist(self, artist_instance: T_Artist, kino_id: str) -> T_Artist:
        """SpotifyServiceを使って最新化し、DBを更新する"""
        try:
            # 1. 外部サービス経由でデータを取得
            # SpotifyService内でspotipyのエラーをExternalServiceError等にラップして投げている前提
            latest_data = self.spotify_service.fetch_artist_detail(artist_instance.spotify_id)
        except ExternalServiceError as e:
            # Spotify側のエラー(ExternalError系)を検知した場合
            # ログ出力を行い、クライアントに返すためのビジネス例外(400/502系)へ変換
            log_output_by_msg_id(
                log_id="MSGE001", 
                params=[f"Spotify service is unavailable: {str(e)}"], 
                logger_name=LOG_METHOD.APPLICATION.value
            )
            # これが ERR_ART_201 (502 Bad Gateway) 等になる
            raise SpotifyLinkageError() from e

        try:
            with transaction.atomic():
                # 2. 基本情報の更新
                artist_instance.name = latest_data.get('name', artist_instance.name)
                artist_instance.genres = latest_data.get('genres', [])

                # 3. 画像URLの同期（変更がある場合のみ）
                images = latest_data.get('images', [])
                if images:
                    new_url = images[0]['url']
                    # 現在の画像URLと異なる場合のみリソースを更新
                    if not artist_instance.spotify_image or artist_instance.spotify_image.external_url != new_url:
                        from apps.common.models import T_FileResource
                        
                        # 新しい画像リソースを作成
                        new_image = T_FileResource.objects.create(
                            file_type=T_FileResource.FileType.IMAGE,
                            external_url=new_url,
                            file_name=f"spotify_{artist_instance.name}_refreshed_{timezone.now().strftime('%Y%m%d')}",
                            created_by_id=artist_instance.user_id,
                            created_method=kino_id,
                            updated_by_id=artist_instance.user_id,
                            updated_method=kino_id,
                        )
                        artist_instance.spotify_image = new_image

                # 4. 保存
                artist_instance.updated_method = kino_id
                artist_instance.save()
                
                return artist_instance

        except Exception as e:
            log_output_by_msg_id(
                log_id="MSGE001", 
                params=[f"Failed to update artist from Spotify: {str(e)}"], 
                logger_name=LOG_METHOD.APPLICATION.value
            )
            raise
    
    def refresh_artists_batch(self, user_profile, artist_queryset, kino_id: str):
        """
        QuerySetを受け取り、その中の全アーティストをSpotifyの最新情報と同期する
        """
        spotify_ids = [a.spotify_id for a in artist_queryset]
        
        # 1. Spotifyから一括取得
        try:
            latest_data_list = self.spotify_service.fetch_artists_batch(spotify_ids)
        except ExternalServiceError as e:
            raise SpotifyLinkageError()

        # 2. データをマッピング（SpotifyIDをキーにした辞書にすると更新が楽）
        latest_map = {data['id']: data for data in latest_data_list}

        # 3. 更新処理
        updated_artists = []
        with transaction.atomic():
            for artist in artist_queryset:
                data = latest_map.get(artist.spotify_id)
                if not data:
                    continue
                
                # ここで1件更新のロジック（get_refreshed_artistの内容）を再利用
                # 大量更新の場合は、画像URLの変更チェックなどを効率化
                artist.name = data.get('name', artist.name)
                artist.genres = data.get('genres', [])
                
                # 共通化した画像更新ロジックを呼び出し
                self._update_spotify_image(artist, data, kino_id)
                
                artist.updated_method = kino_id
                artist.save()
                updated_artists.append(artist)
        
        return updated_artists

    def create_artist(self, user_profile, validated_data, kino_id: str) -> T_Artist:
        """
        アーティストを新規登録する。
        """
        try:
            with transaction.atomic():
                # 1. 画像リソースの処理 (SpotifyのURLがある場合)
                image_url = validated_data.get('image_url')
                spotify_image_instance = None
                
                if image_url:
                    # 外部URLとしてT_FileResourceに登録
                    # 重複を許容せず1URL1リソースにする場合は get_or_create を検討
                    spotify_image_instance = T_FileResource.objects.create(
                        file_type=T_FileResource.FileType.IMAGE,
                        external_url=image_url,
                        file_name=f"spotify_{validated_data['name']}_image",
                        created_by_id=user_profile.user_id, # ProfileのPK(user_id)を使用
                        created_method=kino_id,
                        updated_by_id=user_profile.user_id,
                        updated_method=kino_id,
                    )

                # 2. アーティスト本体の登録
                artist_instance = T_Artist.objects.create(
                    user=user_profile,
                    spotify_id=validated_data['spotify_id'],
                    name=validated_data['name'],
                    spotify_image=spotify_image_instance,
                    context=validated_data.get('context_id'), # Serializer側でインスタンス化されている想定
                    genres=validated_data.get('genres', []),
                    created_by_id=user_profile.user_id,
                    created_method=kino_id,
                    updated_by_id=user_profile.user_id,
                    updated_method=kino_id,
                )

                # 3. タグの紐付け (ManyToMany + throughモデル R_ArtistTag の直接作成)
                tag_instances = validated_data.get('tag_ids')
                if tag_instances:
                    for tag in tag_instances:
                        R_ArtistTag.objects.create(
                            artist=artist_instance,
                            tag=tag,
                            created_by_id=user_profile.user_id,
                            created_method=kino_id,
                            updated_by_id=user_profile.user_id,
                            updated_method=kino_id,
                        )

                return artist_instance

        except IntegrityError as e:
            # ユニーク制約違反（同一ユーザーによる同一SpotifyIDの重複登録など）
            log_output_by_msg_id(
                log_id="MSGE001", 
                params=[f"Artist registration failed due to unique constraint: {str(e)}"], 
                logger_name=LOG_METHOD.APPLICATION.value
            )
            # 独自定義した400系エラーをスロー
            raise ArtistAlreadyExistsError() from e
            
        except Exception as e:
            # その他、予期せぬエラーのログ出力
            log_output_by_msg_id(
                log_id="MSGE001", 
                params=[f"Unexpected error in ArtistService.create_artist: {str(e)}"], 
                logger_name=LOG_METHOD.APPLICATION.value
            )
            # そのまま再送出し、View側の共通処理でキャッチさせる
            raise