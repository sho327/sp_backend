from datetime import datetime

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated

from apps.artist.serializer.artist_base import ArtistFullResponseSerializer

# --- アーティストモジュール ---
from apps.artist.serializer.artist_create import ArtistCreateRequestSerializer
from apps.artist.services import ArtistService
from core.consts import LOG_METHOD

# --- コアモジュール ---
from core.decorators.logging_process_with_sql import logging_process_with_sql
from core.exceptions.exceptions import ApplicationError
from core.utils.date_format import convert_to_site_timezone
from core.utils.log_helpers import log_output_by_msg_id
from core.views import BaseAPIView

KINO_ID = "artist-create"


class ArtistCreateView(BaseAPIView):
    """
    アーティスト登録APIクラス
    Create
        Author: Kato Shogo
    """

    permission_classes = [IsAuthenticated]
    artist_service = ArtistService()

    @logging_process_with_sql
    def post(self, request, *args, **kwargs):
        """
        POSTリクエストを受け付ける。
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
            return self.artist_create(request, *args, **kwargs)
        except ApplicationError:
            raise
        except Exception as e:
            raise ApplicationError() from e

    def artist_create(self, request, *args, **kwargs):
        """
        アーティスト登録処理
        Args:
            request:  HTTPリクエスト
        """
        date_now: datetime = convert_to_site_timezone(timezone.now())
        # 1. 処理開始ログ出力(GETなのでクエリパラメータを出力)
        log_output_by_msg_id(
            log_id="MSGI003",
            params=[KINO_ID, str(request.data)],
            logger_name=LOG_METHOD.APPLICATION.value,
        )

        # 2. リクエストデータ検証
        serializer = ArtistCreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 3. サービス実行(アーティスト登録)
        new_artist = self.artist_service.create_artist(
            date_now=date_now,
            kino_id=KINO_ID,
            user=request.user,
            validated_data=serializer.validated_data,
        )

        # 4. レスポンス作成(Full構成を使用)
        res_serializer = ArtistFullResponseSerializer(new_artist)
        # get_success_map_responseを使用
        response = self.get_success_map_response(
            data=res_serializer.data,
        )

        # 5. 処理終了ログ出力
        log_output_by_msg_id(
            log_id="MSGI004",
            params=[KINO_ID, str(response.data)],
            logger_name=LOG_METHOD.APPLICATION.value,
        )

        # 8. レスポンス返却
        return response
