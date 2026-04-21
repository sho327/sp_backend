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
from apps.artist.serializer.artist_update import ArtistUpdateRequestSerializer
from apps.artist.serializer.artist_base import ArtistFullResponseSerializer
from apps.artist.services import ArtistService

KINO_ID = "artist-update"

class ArtistUpdateView(BaseAPIView):
    """
    アーティスト更新APIクラス
    Create
        Author: Kato Shogo
    """
    permission_classes = [IsAuthenticated]
    artist_service = ArtistService()

    @logging_process_with_sql
    def put(self, request, artist_id, *args, **kwargs):
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
            return self.artist_update(request, artist_id, *args, **kwargs)
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
    def patch(self, request, artist_id, *args, **kwargs):
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
            return self.artist_update(request, artist_id, *args, **kwargs)
        except ApplicationError:
            # ApplicationError関連はカスタムエラー処理が設定されている為そのまま親へスローする
            raise
        except DRF_ValidationError as e:
            # DRFバリデーションエラーは専用エラーに差し替える
            raise ValidationError() from e
        except Exception as e:
            # その他想定外エラーの場合もAPIエラーとする
            raise ApplicationError() from e
    
    def artist_update(self, request, artist_id, *args, **kwargs):
        """
        アーティスト更新処理
        Args:
            request:  HTTPリクエスト
        """
        date_now: datetime = convert_to_site_timezone(timezone.now())
        # 1. 処理開始ログ出力
        log_output_by_msg_id(
            log_id="MSGI003", 
            params=[KINO_ID, str(request.data)], 
            logger_name=LOG_METHOD.APPLICATION.value
        )

        # 2. リクエストデータ検証
        serializer = ArtistUpdateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 3. サービス実行(アーティスト更新)
        update_artist = self.artist_service.update_artist(
            date_now=date_now,
            kino_id=KINO_ID,
            user=request.user,
            artist_id=artist_id,
            validated_data=serializer.validated_data,
        )

        # 4. レスポンス作成(Full構成を使用)
        res_serializer = ArtistFullResponseSerializer(update_artist)
        # get_success_map_responseを使用
        response = self.get_success_map_response(
            data=res_serializer.data,
        )

        # 5. 処理終了ログ出力
        log_output_by_msg_id(
            log_id="MSGI004", 
            params=[KINO_ID, str(response.data)], 
            logger_name=LOG_METHOD.APPLICATION.value
        )
        
        return response
