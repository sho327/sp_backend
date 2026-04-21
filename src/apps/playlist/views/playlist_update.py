from datetime import datetime
from django.utils import timezone
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError as DRF_ValidationError

from apps.playlist.serializer.playlist_base import PlaylistMiniResponseSerializer

# --- プレイリストモジュール ---
from apps.playlist.serializer.playlist_update import PlaylistUpdateRequestSerializer
from apps.playlist.services import PlaylistService

# --- コアモジュール ---
from core.decorators.logging_process_with_sql import logging_process_with_sql
from core.exceptions.exceptions import ApplicationError, ValidationError
from core.utils.date_format import convert_to_site_timezone
from core.views import BaseAPIView
from core.utils.log_helpers import log_output_by_msg_id
from core.consts import LOG_METHOD

KINO_ID = "playlist-update"


class PlaylistUpdateView(BaseAPIView):
    """
    プレイリスト更新APIクラス
    """
    permission_classes = [IsAuthenticated]
    playlist_service = PlaylistService()
    parser_classes = [MultiPartParser, FormParser]

    @logging_process_with_sql
    def put(self, request, playlist_id: str, *args, **kwargs):
        """
        PUTリクエストを受け付ける。
        Method: PUT
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
            return self.playlist_update(request, playlist_id, *args, **kwargs)
        except ApplicationError:
            # ApplicationError関連はカスタムエラー処理が設定されている為そのまま親へスローする
            raise
        except DRF_ValidationError as e:
            # DRFバリデーションエラーは専用エラーに差し替える
            raise ValidationError() from e
        except Exception as e:
            # その他想定外エラーの場合もAPIエラーとする
            raise ApplicationError() from e
    
    @logging_process_with_sql
    def patch(self, request, playlist_id: str, *args, **kwargs):
        """
        PATCHリクエストを受け付ける。
        Method: PATCH
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
            return self.playlist_update(request, playlist_id, *args, **kwargs)
        except ApplicationError:
            # ApplicationError関連はカスタムエラー処理が設定されている為そのまま親へスローする
            raise
        except DRF_ValidationError as e:
            # DRFバリデーションエラーは専用エラーに差し替える
            raise ValidationError() from e
        except Exception as e:
            # その他想定外エラーの場合もAPIエラーとする
            raise ApplicationError() from e

    def playlist_update(self, request, playlist_id: str, *args, **kwargs):
        """
        プレイリスト更新処理
        Args:
            request:  HTTPリクエスト
        """
        date_now: datetime = convert_to_site_timezone(timezone.now())
        # 1. 処理開始ログ出力
        log_output_by_msg_id(
            log_id="MSGI003",
            params=[KINO_ID, f"playlist_id: {playlist_id}, request.data: {str(request.data)}"],
            logger_name=LOG_METHOD.APPLICATION.value,
        )

        # 2. リクエストデータ検証
        # ※内部でrequest.userを基に検証する処理があるため、
        # 指定されたコンテキスト(request)にrequestオブジェクトを含める
        serializer = PlaylistUpdateRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        # 2. サービス実行(プレイリスト更新)
        validated_data = serializer.validated_data
        playlist = self.playlist_service.update_playlist(
            date_now=date_now,
            kino_id=KINO_ID,
            user=request.user,
            playlist_id=playlist_id,
            validated_data=validated_data,
        )

        # 3. レスポンス作成
        res_serializer = PlaylistMiniResponseSerializer(playlist)
        # get_success_map_responseを使用
        response = self.get_success_map_response(
            data=res_serializer.data,
        )

        # 5. 処理終了ログ出力
        log_output_by_msg_id(
            log_id="MSGI004",
            params=[KINO_ID, f"playlist_id: {playlist_id}, response.data: {str(response.data)}"],
            logger_name=LOG_METHOD.APPLICATION.value,
        )

        # 成功レスポンス返却
        return response
