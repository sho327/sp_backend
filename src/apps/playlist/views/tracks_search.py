from datetime import datetime
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError as DRF_ValidationError

# --- プレイリストモジュール ---
from apps.playlist.serializer.tracks_search import TracksSearchRequestSerializer
from apps.playlist.serializer.playlist_track_base import CustomPlaylistTrackResponseSerializer
from apps.playlist.services import PlaylistService

# --- コアモジュール ---
from core.decorators.logging_process_with_sql import logging_process_with_sql
from core.exceptions.exceptions import ApplicationError, ValidationError
from core.utils.date_format import convert_to_site_timezone
from core.views import BaseAPIView
from core.utils.log_helpers import log_output_by_msg_id
from core.consts import LOG_METHOD

KINO_ID = "tracks-search"


class TracksSearchView(BaseAPIView):
    """
    トラック検索APIクラス
    """
    permission_classes = [IsAuthenticated]
    playlist_service = PlaylistService()

    @logging_process_with_sql
    def get(self, request, *args, **kwargs):
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
            return self.tracks_search(request, *args, **kwargs)
        except ApplicationError:
            # ApplicationError関連はカスタムエラー処理が設定されている為そのまま親へスローする
            raise
        except DRF_ValidationError as e:
            # DRFバリデーションエラーは専用エラーに差し替える
            raise ValidationError() from e
        except Exception as e:
            # その他想定外エラーの場合もAPIエラーとする
            raise ApplicationError() from e

    def tracks_search(self, request, *args, **kwargs):
        """
        トラック検索処理
        Args:
            request:  HTTPリクエスト
        """
        date_now: datetime = convert_to_site_timezone(timezone.now())
        # 1. 処理開始ログ出力
        log_output_by_msg_id(
            log_id="MSGI003",
            params=[KINO_ID, f"query_params: {request.query_params}"],
            logger_name=LOG_METHOD.APPLICATION.value,
        )

        # 2. リクエストデータ検証
        # GETなのでrequest.query_paramsを渡す
        serializer = TracksSearchRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        # 3. サービス実行(楽曲生成)
        tracks = self.playlist_service.search_tracks(
            date_now=date_now,
            kino_id=KINO_ID,
            user=request.user,
            validated_data=serializer.validated_data,
        )

        # 4. レスポンス作成
        # 生成された楽曲データをシリアライズ
        res_serializer = CustomPlaylistTrackResponseSerializer(
            tracks, many=True
        )
        # get_success_map_responseを使用
        response = self.get_success_list_response(
            data=res_serializer.data,
        )

        # 5. 処理終了ログ出力
        log_output_by_msg_id(
            log_id="MSGI004",
            params=[KINO_ID, str(response.data)],
            logger_name=LOG_METHOD.APPLICATION.value,
        )

        return response

