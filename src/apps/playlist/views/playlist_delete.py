from datetime import datetime
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated

# --- コアモジュール ---
from core.decorators.logging_process_with_sql import logging_process_with_sql
from core.consts import LOG_METHOD
from core.utils.log_helpers import log_output_by_msg_id
from core.utils.date_format import convert_to_site_timezone
from core.exceptions.exceptions import ApplicationError
from core.views import BaseAPIView

# --- プレイリストモジュール ---
from apps.playlist.services import PlaylistService

KINO_ID = "playlist-delete"

class PlaylistDeleteView(BaseAPIView):
    """
    プレイリスト削除APIクラス
    Create
        Author: Kato Shogo
    """
    permission_classes = [IsAuthenticated]
    playlist_service = PlaylistService()

    @logging_process_with_sql
    def delete(self, request, playlist_id, *args, **kwargs):
        """
        DELETEリクエストを受け付ける。
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
            return self.playlist_delete(request, playlist_id, *args, **kwargs)
        except ApplicationError:
            raise
        except Exception as e:
            raise ApplicationError() from e
    
    def playlist_delete(self, request, playlist_id, *args, **kwargs):
        """
        プレイリスト削除処理
        Args:
            request:  HTTPリクエスト
        """
        date_now: datetime = convert_to_site_timezone(timezone.now())
        # 1. 処理開始ログ出力(GETなのでクエリパラメータを出力)
        log_output_by_msg_id(
            log_id="MSGI003", 
            params=[KINO_ID, f"ID: {playlist_id}"], 
            logger_name=LOG_METHOD.APPLICATION.value
        )
        
        # 2. サービス実行(アーティスト削除)
        self.playlist_service.delete_playlist(
            date_now=date_now,
            kino_id=KINO_ID,
            user=request.user,
            artist_id=playlist_id,
        )

        # 3. レスポンス作成
        # get_success_map_responseを使用(実行日時を含む空のマップを返却)
        response = self.get_success_map_response(data={})

        # 4. 処理終了ログ出力
        log_output_by_msg_id(
            log_id="MSGI004", 
            params=[KINO_ID, f"Deleted ID: {playlist_id}"], 
            logger_name=LOG_METHOD.APPLICATION.value
        )
        
        # 8. レスポンス返却
        return response
