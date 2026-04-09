from django.http import Http404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.playlist.exceptions import PlaylistExternalServiceError, PlaylistNotFoundError
from apps.playlist.models import T_Playlist
from apps.playlist.serializer.model_t_playlist import (
    GeneratePlaylistSerializer,
    PlaylistSerializer,
    ReplaceTracksSerializer,
    SearchTracksSerializer,
)
from apps.playlist.services import PlaylistService
from core.consts import LOG_METHOD
from core.decorators.logging_process_with_sql import logging_process_with_sql
from core.exceptions.exceptions import ApplicationError
from core.utils.log_helpers import log_output_by_msg_id

KINO_ID_BASE = "model-t-playlist"


class Model_T_PlaylistViewSet(viewsets.ModelViewSet):
    """
    プレイリスト CRUD + 生成 + トラック差し替え + トラック検索 ViewSet
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PlaylistSerializer
    playlist_service = PlaylistService()

    def get_queryset(self):
        # ログインユーザー自身の、論理削除されていないプレイリストのみを返す
        # タイムライン表示を想定し、新しい順で返却
        return T_Playlist.objects.filter(
            user=self.request.user.user_t_profile_set,
            deleted_at__isnull=True,
        ).order_by("-created_at")

    # ------------------------------------------------------------------
    # 生成 (POST /api/v1/playlist/model-t_playlist/generate/)
    # ------------------------------------------------------------------
    @logging_process_with_sql(f"{KINO_ID_BASE}_generate")
    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request, *args, **kwargs):
        return self._execute_action(self._perform_generate, request, *args, **kwargs)

    def _perform_generate(self, request, *args, **kwargs):
        """
        プレイリスト生成の実処理
        """
        # 1. 入力バリデーション
        serializer = GeneratePlaylistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # 2. 生成 + DB保存 + Trackset URL生成
            playlist, trackset_urls = self.playlist_service.create_generated_playlist(
                user_profile=request.user.user_t_profile_set,
                params=serializer.validated_data,
                kino_id=f"{KINO_ID_BASE}_generate",
            )
        except ApplicationError:
            raise
        except Exception as e:
            # 外部連携失敗はドメイン例外へ寄せる
            raise PlaylistExternalServiceError() from e

        # 3. レスポンス返却
        return Response(
            {"playlist": self.get_serializer(playlist).data, "trackset_urls": trackset_urls},
            status_code=status.HTTP_201_CREATED,
        )

    # ------------------------------------------------------------------
    # トラック差し替え (POST /api/v1/playlist/model-t_playlist/{id}/replace-tracks/)
    # ------------------------------------------------------------------
    @logging_process_with_sql(f"{KINO_ID_BASE}_replace_tracks")
    @action(detail=True, methods=["post"], url_path="replace-tracks")
    def replace_tracks(self, request, *args, **kwargs):
        return self._execute_action(self._perform_replace_tracks, request, *args, **kwargs)

    def _perform_replace_tracks(self, request, *args, **kwargs):
        """
        既存プレイリストのトラック明細を差し替える実処理
        """
        # 1. 入力バリデーション(track_ids)
        serializer = ReplaceTracksSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 2. 対象プレイリストを取得(存在しない場合は PlaylistNotFoundError)
        playlist = self.get_object()

        # 3. サービスで明細差し替え
        payload = self.playlist_service.replace_tracks(
            playlist=playlist,
            track_ids=serializer.validated_data["track_ids"],
            kino_id=f"{KINO_ID_BASE}_replace_tracks",
        )

        # 4. 結果返却
        return Response(payload, status_code=status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # トラック検索 (GET /api/v1/playlist/model-t_playlist/search-tracks/?...)
    # ------------------------------------------------------------------
    @logging_process_with_sql(f"{KINO_ID_BASE}_search_tracks")
    @action(detail=False, methods=["get"], url_path="search-tracks")
    def search_tracks(self, request, *args, **kwargs):
        return self._execute_action(self._perform_search_tracks, request, *args, **kwargs)

    def _perform_search_tracks(self, request, *args, **kwargs):
        """
        アーティストを絞ったSpotifyトラック検索の実処理
        """
        # 1. クエリパラメータのバリデーション
        serializer = SearchTracksSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # 2. サービスで検索
        payload = self.playlist_service.search_tracks(
            artist_spotify_id=data["artist_spotify_id"],
            q=data["q"],
            limit=data["limit"],
        )

        # 3. 検索結果返却
        return Response(payload, status_code=status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # 一覧取得 (GET /api/v1/playlist/model-t_playlist/)
    # ------------------------------------------------------------------
    @logging_process_with_sql(f"{KINO_ID_BASE}_list")
    def list(self, request, *args, **kwargs):
        return self._execute_action(self._perform_list, request, *args, **kwargs)

    def _perform_list(self, request, *args, **kwargs):
        """
        一覧取得の実処理
        """
        # 1. ユーザー範囲のクエリセットを取得
        queryset = self.filter_queryset(self.get_queryset())

        # 2. ページネーション適用(有効時)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # 3. ページネーション未使用時のフォールバック
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status_code=status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # 詳細取得 (GET /api/v1/playlist/model-t_playlist/{id}/)
    # ------------------------------------------------------------------
    @logging_process_with_sql(f"{KINO_ID_BASE}_retrieve")
    def retrieve(self, request, *args, **kwargs):
        return self._execute_action(self._perform_retrieve, request, *args, **kwargs)

    def _perform_retrieve(self, request, *args, **kwargs):
        """
        詳細取得の実処理
        """
        # 1. 対象プレイリストを取得
        instance = self.get_object()

        # 2. レスポンス整形
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status_code=status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # 更新 (PATCH /api/v1/playlist/model-t_playlist/{id}/)
    # ------------------------------------------------------------------
    @logging_process_with_sql(f"{KINO_ID_BASE}_partial_update")
    def partial_update(self, request, *args, **kwargs):
        return self._execute_action(self._perform_partial_update, request, *args, **kwargs)

    def _perform_partial_update(self, request, *args, **kwargs):
        """
        部分更新の実処理
        """
        # 1. 対象取得
        instance = self.get_object()

        # 2. DRF標準のpartial serializerで更新
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # 3. 更新後の値を返却
        return Response(serializer.data, status_code=status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # 削除 (DELETE /api/v1/playlist/model-t_playlist/{id}/)
    # ------------------------------------------------------------------
    @logging_process_with_sql(f"{KINO_ID_BASE}_delete")
    def destroy(self, request, *args, **kwargs):
        return self._execute_action(self._perform_destroy, request, *args, **kwargs)

    def _perform_destroy(self, request, *args, **kwargs):
        """
        削除の実処理(論理削除)
        """
        # 1. 対象取得
        instance = self.get_object()

        # 2. 論理削除実行
        self.perform_destroy(instance)

        # 3. 削除成功レスポンス
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        """論理削除"""
        instance.updated_by_id = self.request.user.id
        instance.updated_method = f"{KINO_ID_BASE}_delete"
        instance.deleted_at = timezone.now()
        instance.save()

    def get_object(self):
        # 404をPlaylistドメイン例外へ変換して一貫性を保つ
        try:
            return super().get_object()
        except Http404 as e:
            raise PlaylistNotFoundError() from e

    def _execute_action(self, action_func, request, *args, **kwargs):
        """
        artist側と同様の共通実行メソッド
        - 開始ログ
        - 本処理実行
        - 終了ログ
        - 想定外例外の ApplicationError 変換
        """
        kino_id = f"{KINO_ID_BASE}_{self.action}"
        log_output_by_msg_id(
            log_id="MSGI003",
            params=[kino_id, str(request.query_params if request.method == "GET" else request.data)],
            logger_name=LOG_METHOD.APPLICATION.value,
        )
        try:
            response = action_func(request, *args, **kwargs)
            log_output_by_msg_id(
                log_id="MSGI004",
                params=[kino_id, str(getattr(response, "data", ""))],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            return response
        except (ApplicationError, APIException, Http404):
            raise
        except Exception as e:
            raise ApplicationError() from e