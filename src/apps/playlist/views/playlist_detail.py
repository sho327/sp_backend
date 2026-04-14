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
from apps.playlist.serializer.playlist_detail import PlaylistDetailRequestSerializer
from apps.playlist.serializer.playlist_base import PlaylistFullResponseSerializer
from apps.playlist.services import PlaylistService

KINO_ID = "playlist-detail"

class PlaylistDetailView(BaseAPIView):
    """
    プレイリスト詳細取得APIクラス
    Create
        Author: Kato Shogo
    """
    permission_classes = [IsAuthenticated]
    playlist_service = PlaylistService()

    @logging_process_with_sql
    def get(self, request, playlist_id, *args, **kwargs):
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
            return self.playlist_detail(request, playlist_id, *args, **kwargs)
        except ApplicationError:
            raise
        except Exception as e:
            raise ApplicationError() from e
    
    def playlist_detail(self, request, playlist_id, *args, **kwargs):
        """
        プレイリスト登録処理
        Args:
            request:  HTTPリクエスト
        """
        date_now: datetime = convert_to_site_timezone(timezone.now())
        # 1. 処理開始ログ出力(GETなのでクエリパラメータを出力)
        log_output_by_msg_id(
            log_id="MSGI003", 
            params=[KINO_ID, f"ID: {playlist_id}, Params: {request.query_params}"], 
            logger_name=LOG_METHOD.APPLICATION.value
        )

        # 2. リクエストデータ検証
        # GETなのでrequest.query_paramsを渡す
        serializer = PlaylistDetailRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        # リクエストデータ変数化
        refresh = serializer.validated_data.get('refresh')
        
        # 3. サービス実行(プレイリスト詳細取得)
        playlist = self.playlist_service.detail_playlist(
            date_now=date_now,
            kino_id=KINO_ID,
            user=request.user,
            playlist_id=playlist_id,
        )

        # 4. Spotify最新化判定
        if refresh:
            # サービス実行(アーティスト情報最新化)※SpotifyAPI使用
            # サービス側で更新。引数にはインスタンスを渡す
            playlist = self.playlist_service.refresh_playlist_tracks(
                date_now=date_now,
                kino_id=KINO_ID,
                user=request.user,
                playlist_instance=playlist,
            )

        # 5. レスポンス作成(Full構成を使用)
        res_serializer = PlaylistFullResponseSerializer(playlist)
        # get_success_map_responseを使用
        response = self.get_success_map_response(
            data=res_serializer.data,
        )

        # 6. 処理終了ログ出力
        log_output_by_msg_id(
            log_id="MSGI004", 
            params=[KINO_ID, f"ID: {playlist_id}, Refreshed: {refresh}"], 
            logger_name=LOG_METHOD.APPLICATION.value
        )

        # 7. レスポンス返却
        return response
