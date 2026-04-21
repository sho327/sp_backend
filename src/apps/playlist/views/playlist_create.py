from datetime import datetime
from django.utils import timezone
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError as DRF_ValidationError

# --- コアモジュール ---
from core.decorators.logging_process_with_sql import logging_process_with_sql
from core.views import BaseAPIView
from core.utils.date_format import convert_to_site_timezone
from core.exceptions.exceptions import ApplicationError, ValidationError
from core.utils.log_helpers import log_output_by_msg_id
from core.consts import LOG_METHOD

# --- プレイリストモジュール ---
from apps.playlist.serializer.playlist_create import PlaylistCreateRequestSerializer
from apps.playlist.serializer.playlist_track_base import CustomPlaylistTrackRequestSerializer
from apps.playlist.serializer.playlist_base import PlaylistMiniResponseSerializer
from apps.playlist.services import PlaylistService

KINO_ID = "playlist-create"

class PlaylistCreateView(BaseAPIView):
    """
    プレイリスト作成APIクラス
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    playlist_service = PlaylistService()

    @logging_process_with_sql
    def post(self, request, *args, **kwargs):
        """
        POSTリクエストを受け付ける。
        Method: POST
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
            return self.playlist_create(request, *args, **kwargs)
        except ApplicationError:
            # ApplicationError関連はカスタムエラー処理が設定されている為そのまま親へスローする
            raise
        except DRF_ValidationError as e:
            # DRFバリデーションエラーは専用エラーに差し替える
            raise ValidationError() from e
        except Exception as e:
            # その他想定外エラーの場合もAPIエラーとする
            raise ApplicationError() from e

    def playlist_create(self, request, *args, **kwargs):
        """
        プレイリスト作成処理
        Args:
            request:  HTTPリクエスト
        """
        date_now: datetime = convert_to_site_timezone(timezone.now())
        # 1. 処理開始ログ出力
        log_output_by_msg_id(
            log_id="MSGI003",
            params=[KINO_ID, str(request.data)],
            logger_name=LOG_METHOD.APPLICATION.value,
        )
        
        # 2. リクエストデータ検証
        # ※内部でrequest.userを基に検証する処理があるため、
        # 指定されたコンテキスト(request)にrequestオブジェクトを含める
        serializer = PlaylistCreateRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        # 3. サービス実行(プレイリスト作成/トラック登録)
        playlist = self.playlist_service.create_playlist(
            date_now=date_now,
            kino_id=KINO_ID,
            user=request.user,
            validated_data=serializer.validated_data,
        )
        
        # 4. レスポンス作成
        res_serializer = PlaylistMiniResponseSerializer(playlist)
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

        return response
