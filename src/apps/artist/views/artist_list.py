from datetime import datetime
from django.utils import timezone
from django.core.paginator import Paginator
from rest_framework.permissions import IsAuthenticated

# --- コアモジュール ---
from core.decorators.logging_process_with_sql import logging_process_with_sql
from core.consts import LOG_METHOD
from core.utils.log_helpers import log_output_by_msg_id
from core.utils.date_format import convert_to_site_timezone
from core.exceptions.exceptions import ApplicationError
from core.views import BaseAPIView

# --- アーティストモジュール ---
from apps.artist.serializer.artist_list import ArtistListRequestSerializer
from apps.artist.serializer.artist_base import ArtistMiniResponseSerializer
from apps.artist.services import ArtistService

KINO_ID = "artist-list"

class ArtistListView(BaseAPIView):
    """
    アーティスト一覧取得APIクラス
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
            return self.artist_list(request, *args, **kwargs)
        except ApplicationError:
            raise
        except Exception as e:
            raise ApplicationError() from e
    
    def artist_list(self, request, *args, **kwargs):
        """
        アーティスト一覧取得処理
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
        serializer = ArtistListRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        # リクエストデータ変数化
        name = serializer.validated_data.get("name")
        tag_ids = serializer.validated_data("tag_ids")
        per_page = serializer.validated_data.get("per_page")
        page = serializer.validated_data.get("page")
        refresh = serializer.validated_data.get('refresh')
        
        # 3. サービス実行(一覧データ取得)
        # Service側で select_related('spotify_image') 等のN+1対策がなされたQuerySetを取得
        queryset = self.artist_service.list_artist(
            date_now=date_now,
            kino_id=KINO_ID,
            user=request.user,
            name=name,
            tag_ids=tag_ids,
        )

        # 4. ページング処理
        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page)

        # 5. Spotify最新化判定
        # リクエストに refresh=true があり、かつデータが存在する場合
        if refresh and page_obj.object_list:
            # サービス実行(アーティスト情報最新化)※SpotifyAPI使用
            # サービス側で一括更新。引数には現在のページのインスタンスリストを渡す
            self.artist_service.refresh_artists(
                date_now=date_now,
                kino_id=f"{KINO_ID}",
                user=request.user,
                artist_queryset=page_obj.object_list,
            )

        # 6. レスポンス作成(Mini構成を使用)
        # many=Trueでリスト形式としてシリアライズ
        res_serializer = ArtistMiniResponseSerializer(page_obj.object_list, many=True)
        # get_success_list_response を使用し、results/countを含む共通フォーマットを生成
        response = self.get_success_list_response(
            data=res_serializer.data,
            count=paginator.count
        )

        # 7. 処理終了ログ出力
        log_output_by_msg_id(
            log_id="MSGI004", 
            params=[KINO_ID, f"page: {serializer.validated_data.get("page")}, count: {paginator.count}"], 
            logger_name=LOG_METHOD.APPLICATION.value
        )
        
        # 8. レスポンス返却
        return response
