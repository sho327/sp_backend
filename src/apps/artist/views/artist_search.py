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
from apps.artist.serializer.artist_search import ArtistSearchRequestSerializer, ArtistSearchResponseSerializer
from apps.artist.services import ArtistService

KINO_ID = "artist-search"

class ArtistSearchView(BaseAPIView):
    """
    アーティスト検索APIクラス
    Create
        Author: Kato Shogo
    """
    permission_classes = [IsAuthenticated]
    artist_service = ArtistService()

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
            return self.artist_search(request, *args, **kwargs)
        except ApplicationError:
            # ApplicationError関連はカスタムエラー処理が設定されている為そのまま親へスローする
            raise
        except DRF_ValidationError as e:
            # DRFバリデーションエラーは専用エラーに差し替える
            raise ValidationError() from e
        except Exception as e:
            # その他想定外エラーの場合もAPIエラーとする
            raise ApplicationError() from e
    
    def artist_search(self, request, *args, **kwargs):
        """
        アーティスト検索処理
        Args:
            request:  HTTPリクエスト
        """
        date_now: datetime = convert_to_site_timezone(timezone.now())
        # 1. 処理開始ログ出力(GETなのでクエリパラメータを出力)
        log_output_by_msg_id(
            log_id="MSGI003", 
            params=[KINO_ID, str(request.query_params)], 
            logger_name=LOG_METHOD.APPLICATION.value
        )

        # 2. リクエストデータ検証
        # GETなのでrequest.query_paramsを渡す
        serializer = ArtistSearchRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        # 3. サービス実行(アーティスト検索)※DeezerAPI使用
        raw_results = self.artist_service.search_artist(
            date_now=date_now,
            kino_id=KINO_ID,
            user=request.user,
            validated_data=serializer.validated_data,
        )

        # 4. レスポンス作成(Mini構成を使用)
        # many=Trueでリスト形式としてシリアライズ
        res_serializer = ArtistSearchResponseSerializer(raw_results, many=True)
        # get_success_list_response を使用し、results/countを含む共通フォーマットを生成
        response = self.get_success_list_response(
            data=res_serializer.data,
            count=len(raw_results),
        )

        # 5. 処理終了ログ出力
        log_output_by_msg_id(
            log_id="MSGI004", 
            params=[KINO_ID, f"results_count: {len(raw_results)}"], 
            logger_name=LOG_METHOD.APPLICATION.value
        )
        
        return response
