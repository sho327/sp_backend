from datetime import datetime
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError as DRF_ValidationError

# --- コアモジュール ---
from core.decorators.logging_process_with_sql import logging_process_with_sql
from core.consts import LOG_METHOD
from core.utils.log_helpers import log_output_by_msg_id
from core.utils.date_format import convert_to_site_timezone
from core.exceptions.exceptions import ApplicationError, ValidationError
from core.views import BaseAPIView

# --- アーティストモジュール ---
from apps.artist.serializer.artist_detail import ArtistDetailRequestSerializer
from apps.artist.serializer.artist_base import ArtistFullResponseSerializer
from apps.artist.services import ArtistService

KINO_ID = "artist-detail"

class ArtistDetailView(BaseAPIView):
    """
    アーティスト詳細取得APIクラス
    Create
        Author: Kato Shogo
    """
    permission_classes = [IsAuthenticated]
    artist_service = ArtistService()

    @logging_process_with_sql
    def get(self, request, artist_id, *args, **kwargs):
        """
        GETリクエストを受け付ける。
        Method: GET
        Args:
            request:  HTTPリクエスト
            *args:    引数
            **kwargs: キーワード引数
        Returns:
            Response: HTTPレスポンス
        Raises:
            InternalServerError: 想定外エラー
        """
        try:
            return self.artist_detail(request, artist_id, *args, **kwargs)
        except ApplicationError:
            # ApplicationError関連はカスタムエラー処理が設定されている為そのまま親へスローする
            raise
        except DRF_ValidationError as e:
            # DRFバリデーションエラーは専用エラーに差し替える
            raise ValidationError() from e
        except Exception as e:
            # その他想定外エラーの場合もAPIエラーとする
            raise ApplicationError() from e
    
    def artist_detail(self, request, artist_id, *args, **kwargs):
        """
        アーティスト登録処理
        Args:
            request:  HTTPリクエスト
        """
        date_now: datetime = convert_to_site_timezone(timezone.now())
        # 1. 処理開始ログ出力(GETなのでクエリパラメータを出力)
        log_output_by_msg_id(
            log_id="MSGI003", 
            params=[KINO_ID, f"ID: {artist_id}, Params: {request.query_params}"], 
            logger_name=LOG_METHOD.APPLICATION.value
        )

        # 2. リクエストデータ検証
        # GETなのでrequest.query_paramsを渡す
        serializer = ArtistDetailRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        # リクエストデータ変数化
        refresh = serializer.validated_data.get('refresh')
        
        # 3. サービス実行(アーティスト詳細取得)
        artist = self.artist_service.detail_artist(
            date_now=date_now,
            kino_id=KINO_ID,
            user=request.user,
            artist_id=artist_id,
        )

        # 4. Spotify最新化判定
        if refresh:
            # サービス実行(アーティスト情報最新化)※SpotifyAPI使用
            # サービス側で更新。引数にはインスタンスを渡す
            artist = self.artist_service.refresh_artist(
                date_now=date_now,
                kino_id=KINO_ID,
                user=request.user,
                artist_instance=artist,
            )

        # 5. レスポンス作成(Full構成を使用)
        res_serializer = ArtistFullResponseSerializer(artist)
        # get_success_map_responseを使用
        response = self.get_success_map_response(
            data=res_serializer.data,
        )

        # 6. 処理終了ログ出力
        log_output_by_msg_id(
            log_id="MSGI004", 
            params=[KINO_ID, f"ID: {artist_id}, Refreshed: {refresh}"], 
            logger_name=LOG_METHOD.APPLICATION.value
        )

        return response
