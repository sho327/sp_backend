from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.http import Http404
from rest_framework.exceptions import APIException

# --- コアモジュール ---
from core.decorators.logging_process_with_sql import logging_process_with_sql
from core.consts import LOG_METHOD
from core.utils.log_helpers import log_output_by_msg_id
from core.utils.date_format import convert_to_site_timezone, date_to_str
from core.exceptions.exceptions import ApplicationError
# --- アカウントモジュール ---
from apps.account.models.masters import M_User
# --- アーティストモジュール ---
from apps.artist.models import M_ArtistTag
from apps.artist.serializer.model_m_artist_tag import Model_M_ArtistTagSerializer

KINO_ID_BASE = "model-m-artist-tags"

class Model_M_ArtistTagViewSet(viewsets.ModelViewSet):
    """
    アーティストタグマスタ CRUD ViewSet
    """
    serializer_class = Model_M_ArtistTagSerializer

    def get_queryset(self):
        # 有効な（論理削除されていない）タグのみを返す
        return M_ArtistTag.objects.filter(deleted_at__isnull=True).order_by('name')

    # ------------------------------------------------------------------
    # 一覧取得 (GET /api/model-m_artist_tags/)
    # ------------------------------------------------------------------
    @logging_process_with_sql(f"{KINO_ID_BASE}_list")
    def list(self, request, *args, **kwargs):
        return self._execute_action(super().list, request, *args, **kwargs)

    # ------------------------------------------------------------------
    # 登録 (POST /api/model-m_artist_tags/)
    # ------------------------------------------------------------------
    @logging_process_with_sql(f"{KINO_ID_BASE}_create")
    def create(self, request, *args, **kwargs):
        return self._execute_action(super().create, request, *args, **kwargs)

    # ------------------------------------------------------------------
    # 詳細取得 (GET /api/model-m_artist_tags/{id}/)
    # ------------------------------------------------------------------
    @logging_process_with_sql(f"{KINO_ID_BASE}_retrieve")
    def retrieve(self, request, *args, **kwargs):
        return self._execute_action(super().retrieve, request, *args, **kwargs)

    # ------------------------------------------------------------------
    # 更新 (PUT/PATCH /api/model-m_artist_tags/{id}/)
    # ------------------------------------------------------------------
    @logging_process_with_sql(f"{KINO_ID_BASE}_update")
    def update(self, request, *args, **kwargs):
        return self._execute_action(super().update, request, *args, **kwargs)

    # ------------------------------------------------------------------
    # 削除 (DELETE /api/model-m_artist_tags/{id}/)
    # ------------------------------------------------------------------
    @logging_process_with_sql(f"{KINO_ID_BASE}_delete")
    def destroy(self, request, *args, **kwargs):
        # 内部で perform_destroy が呼ばれる
        return self._execute_action(super().destroy, request, *args, **kwargs)
    
    # ------------------------------------------------------------------
    # 共通実行メソッド (ログ・例外ハンドリング集約)
    # ------------------------------------------------------------------
    def _execute_action(self, action_func, request, *args, **kwargs):
        """
        ViewSetの各アクションを実行し、ログ出力と例外ハンドリングを行う
        """
        # partial_update(PATCH) の場合も update としてログを出すための考慮
        action_name = self.action
        if action_name == 'partial_update':
            action_name = 'update'
            
        kino_id = f"{KINO_ID_BASE}_{action_name}"

        # 1. 開始ログ出力
        log_output_by_msg_id(
            log_id="MSGI003", 
            params=[kino_id, str(request.query_params if request.method == 'GET' else request.data)], 
            logger_name=LOG_METHOD.APPLICATION.value
        )

        try:
            # 2. アクションの実行
            response = action_func(request, *args, **kwargs)
            
            # 3. 終了ログ出力
            log_output_by_msg_id(
                log_id="MSGI004", 
                params=[kino_id, str(response.data)], 
                logger_name=LOG_METHOD.APPLICATION.value
            )
            return response

        except (ApplicationError, APIException, Http404):
            # これらはDRFやカスタムハンドラが適切なコード(404, 403等)を返すべきものなので
            # そのまま親へスローする
            raise
        except Exception as e:
            # 想定外エラーのラップ
            raise ApplicationError() from e

    def perform_destroy(self, instance: M_User):
        """物理削除を論理削除に書き換える"""
        instance.updated_by=self.request.user
        instance.updated_method=f"{KINO_ID_BASE}_delete"
        instance.deleted_at = timezone.now()
        instance.save()