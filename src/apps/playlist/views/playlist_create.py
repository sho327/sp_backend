from datetime import datetime
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated

# --- コアモジュール ---
from core.decorators.logging_process_with_sql import logging_process_with_sql
from core.views import BaseAPIView
from core.utils.date_format import convert_to_site_timezone
from core.exceptions.exceptions import ApplicationError

# --- プレイリストモジュール ---
from apps.playlist.serializer.playlist_create import PlaylistCreateRequestSerializer
from apps.playlist.serializer.playlist_base import PlaylistMiniResponseSerializer
from apps.playlist.services import PlaylistService

KINO_ID = "playlist-create"

class PlaylistCreateView(BaseAPIView):
    """
    プレイリスト作成APIクラス
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
            serializer = PlaylistCreateRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # 2. サービス実行（プレイリスト作成 + トラック登録）
            # tracks が request.data に含まれている前提
            # 必要に応じて tracks のバリデーションも行うべきだが、一旦サービスに渡す
            validated_data = serializer.validated_data
            validated_data["tracks"] = request.data.get("tracks", [])
            
            playlist = self.playlist_service.create_playlist(
                date_now=date_now,
                kino_id=KINO_ID,
                user=request.user,
                validated_data=validated_data
            )
            
            # 3. レスポンス作成
            res_serializer = PlaylistMiniResponseSerializer(playlist)
            
            # 成功レスポンス返却
            return self.get_success_map_response(res_serializer.data)

        except ApplicationError:
            raise
        except Exception as e:
            raise ApplicationError() from e
