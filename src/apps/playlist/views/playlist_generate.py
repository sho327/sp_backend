from datetime import datetime

from django.utils import timezone
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

# --- プレイリストモジュール ---
from apps.playlist.serializer.playlist_genarate import (
    PlaylistGenerateRequestSerializer,
    PlaylistTrackGenerateResponseSerializer,
)
from apps.playlist.services import PlaylistService

# --- コアモジュール ---
from core.decorators.logging_process_with_sql import logging_process_with_sql
from core.exceptions.exceptions import ApplicationError
from core.utils.date_format import convert_to_site_timezone
from core.views import BaseAPIView

KINO_ID = "playlist-generate"


class PlaylistGenerateView(BaseAPIView):
    """
    プレイリスト楽曲生成APIクラス
    """

    permission_classes = [IsAuthenticated]
    playlist_service = PlaylistService()

    @logging_process_with_sql
    def post(self, request, *args, **kwargs):
        """
        POSTリクエストを受け付ける。
        Method: POST
        """
        try:
            date_now: datetime = convert_to_site_timezone(timezone.now())

            # 1. バリデーション
            serializer = PlaylistGenerateRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # 2. サービス実行（楽曲生成）
            # 注意: generate_playlist_tracks は List[dict] を返すように修正済み
            tracks_data = self.playlist_service.generate_playlist_tracks(
                date_now=date_now,
                kino_id=KINO_ID,
                user=request.user,
                validated_data=serializer.validated_data,
            )

            # 3. レスポンス作成
            # 生成された楽曲データをシリアライズ
            res_tracks_serializer = PlaylistTrackGenerateResponseSerializer(
                tracks_data, many=True
            )

            # 成功レスポンス返却
            return self.get_success_list_response(res_tracks_serializer.data)

        except ApplicationError:
            raise
        except Exception as e:
            raise ApplicationError() from e
