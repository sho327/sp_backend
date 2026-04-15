from datetime import datetime

from django.utils import timezone
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from apps.playlist.serializer.playlist_base import PlaylistMiniResponseSerializer

# --- プレイリストモジュール ---
from apps.playlist.serializer.playlist_update import PlaylistUpdateRequestSerializer
from apps.playlist.services import PlaylistService

# --- コアモジュール ---
from core.decorators.logging_process_with_sql import logging_process_with_sql
from core.exceptions.exceptions import ApplicationError
from core.utils.date_format import convert_to_site_timezone
from core.views import BaseAPIView

KINO_ID = "playlist-update"


class PlaylistUpdateView(BaseAPIView):
    """
    プレイリスト更新APIクラス
    """

    permission_classes = [IsAuthenticated]
    playlist_service = PlaylistService()
    parser_classes = [MultiPartParser, FormParser]

    @logging_process_with_sql
    def post(self, request, *args, **kwargs):
        """
        POSTリクエストを受け付ける。
        Method: POST
        """
        try:
            date_now: datetime = convert_to_site_timezone(timezone.now())

            # 1. バリデーション
            serializer = PlaylistUpdateRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # 2. サービス実行(プレイリスト更新)
            validated_data = serializer.validated_data
            playlist = self.playlist_service.create_playlist(
                date_now=date_now,
                kino_id=KINO_ID,
                user=request.user,
                validated_data=validated_data,
            )

            # 3. レスポンス作成
            res_serializer = PlaylistMiniResponseSerializer(playlist)

            # 成功レスポンス返却
            return self.get_success_map_response(res_serializer.data)

        except ApplicationError:
            raise
        except Exception as e:
            raise ApplicationError() from e
