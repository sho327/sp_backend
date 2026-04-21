from django.utils import timezone
from rest_framework import viewsets
from django.http import Http404
from rest_framework.exceptions import APIException, ValidationError as DRF_ValidationError

# --- コアモジュール ---
from core.decorators.logging_process_with_sql import logging_process_with_sql
from core.consts import LOG_METHOD
from core.utils.log_helpers import log_output_by_msg_id
from core.exceptions.exceptions import ApplicationError, ValidationError
from core.views import CommonResponseMixin

# --- アーティストモジュール ---
from apps.artist.models import M_ArtistTag
from apps.artist.serializer.master_artist_tag_base import MasterArtistTagMiniResponseSerializer

KINO_ID_BASE = "master-artist-tags"

class M_ArtistTagViewSet(CommonResponseMixin, viewsets.ModelViewSet):
    """
    アーティストタグマスタ CRUD ViewSet
    """
    serializer_class = MasterArtistTagMiniResponseSerializer

    # ------------------------------------------------------------------
    # Django標準メソッドのオーバーライド
    # ------------------------------------------------------------------
    def get_queryset(self):
        # 有効な（論理削除されていない）タグのみを返す
        return M_ArtistTag.objects.filter(deleted_at__isnull=True).order_by('name')
    
    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            created_method=f"{KINO_ID_BASE}_create",
            updated_by=self.request.user,
            updated_method=f"{KINO_ID_BASE}_create"
        )

    def perform_update(self, serializer):
        serializer.save(
            updated_by=self.request.user,
            updated_method=f"{KINO_ID_BASE}_update"
        )
    
    def perform_destroy(self, instance: M_ArtistTag):
        """物理削除を論理削除に書き換える"""
        instance.updated_by=self.request.user
        instance.updated_method=f"{KINO_ID_BASE}_delete"
        instance.deleted_at = timezone.now()
        instance.save()

    # ------------------------------------------------------------------
    # 一覧取得 (GET /master_artist_tags/)
    # ------------------------------------------------------------------
    @logging_process_with_sql
    def list(self, request, *args, **kwargs):
        return self._execute_action(super().list, request, *args, **kwargs)

    # ------------------------------------------------------------------
    # 登録 (POST /master_artist_tags/)
    # ------------------------------------------------------------------
    @logging_process_with_sql
    def create(self, request, *args, **kwargs):
        return self._execute_action(super().create, request, *args, **kwargs)

    # ------------------------------------------------------------------
    # 詳細取得 (GET /master_artist_tags/{id}/)
    # ------------------------------------------------------------------
    @logging_process_with_sql
    def retrieve(self, request, *args, **kwargs):
        return self._execute_action(super().retrieve, request, *args, **kwargs)

    # ------------------------------------------------------------------
    # 更新 (PUT/PATCH /master_artist_tags/{id}/)
    # ------------------------------------------------------------------
    @logging_process_with_sql
    def update(self, request, *args, **kwargs):
        return self._execute_action(super().update, request, *args, **kwargs)

    # ------------------------------------------------------------------
    # 削除 (DELETE /master_artist_tags/{id}/)
    # ------------------------------------------------------------------
    @logging_process_with_sql
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
        # partial_update(PATCH) の場合もupdateとしてログを出すための考慮
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
            # ApplicationError関連はカスタムエラー処理が設定されている為そのまま親へスローする
            # これらはDRFやカスタムハンドラが適切なコード(404, 403等)を返すべきものなのでそのまま親へスローする
            raise
        except DRF_ValidationError as e:
            # DRFバリデーションエラーは専用エラーに差し替える
            raise ValidationError() from e
        except Exception as e:
            # その他想定外エラーの場合もAPIエラーとする
            raise ApplicationError() from e
