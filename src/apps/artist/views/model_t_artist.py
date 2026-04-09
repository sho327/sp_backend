from django.http import Http404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# --- アーティストモジュール ---
from apps.artist.models import T_Artist
from apps.artist.serializer.model_t_artist import Model_T_ArtistSerializer
from apps.artist.serializer.model_t_artist_create import Model_T_ArtistCreateSerializer
from apps.artist.services import ArtistService
from core.consts import LOG_METHOD

# --- コアモジュール ---
from core.decorators.logging_process_with_sql import logging_process_with_sql
from core.exceptions.exceptions import ApplicationError
from core.utils.date_format import convert_to_site_timezone
from core.utils.log_helpers import log_output_by_msg_id

KINO_ID_BASE = "model-t-artist"


class Model_T_ArtistViewSet(viewsets.ModelViewSet):
    """
    アーティストトラン CRUD ViewSet
    """

    permission_classes = [IsAuthenticated]
    serializer_class = Model_T_ArtistSerializer
    artist_service = ArtistService()

    def get_queryset(self):
        # ログインユーザー自身の、論理削除されていないアーティストのみを返す
        return T_Artist.objects.filter(
            user=self.request.user.user_t_profile_set, deleted_at__isnull=True
        ).order_by("-created_at")

    # ------------------------------------------------------------------
    # 一覧取得 (GET /api/t-artists/?refresh=true)
    # ------------------------------------------------------------------
    @logging_process_with_sql(f"{KINO_ID_BASE}_list")
    def list(self, request, *args, **kwargs):
        return self._execute_action(self._perform_list, request, *args, **kwargs)

    def _perform_list(self, request, *args, **kwargs):
        """
        一覧取得の実処理（リフレッシュ機能付き）
        """
        # 1. クエリセットの取得（ログインユーザーの有効なアーティスト）
        queryset = self.filter_queryset(self.get_queryset())

        # 2. ページネーションの実行
        # 先にページネーションを行うことで、更新対象を「今見ているページ」に限定する
        page = self.paginate_queryset(queryset)

        # 3. リフレッシュ判定
        is_refresh = request.query_params.get("refresh") == "true"

        if is_refresh and page is not None:
            # サービスを呼び出して、このページ内のアーティストを一括最新化
            # pageはリスト形式になっているので、そのままサービスに渡す
            self.artist_service.refresh_artists_batch(
                user_profile=request.user.user_t_profile_set,
                artist_queryset=page,
                kino_id=f"{KINO_ID_BASE}_list_refresh",
            )
            # 更新後のデータを再取得（インスタンスをリフレッシュするため）
            # もしくはサービスから返ってきたリストをそのまま使う

        # 4. レスポンスの生成
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # ページネーション未使用時のフォールバック
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # 詳細取得 (GET /api/t-artists/{id}/)
    # ------------------------------------------------------------------
    @logging_process_with_sql(f"{KINO_ID_BASE}_retrieve")
    def retrieve(self, request, *args, **kwargs):
        return self._execute_action(self._perform_retrieve, request, *args, **kwargs)

    def _perform_retrieve(self, request, *args, **kwargs):
        """
        詳細取得の実処理
        """
        # 1. DBから対象レコードを取得（見つからなければ404）
        instance = self.get_object()

        # 2. クエリパラメータ 'refresh' が 'true' ならSpotifyと同期
        is_refresh = request.query_params.get("refresh") == "true"
        if is_refresh:
            # Serviceを呼び出してDBを最新化
            instance = self.artist_service.get_refreshed_artist(
                artist_instance=instance, kino_id=f"{KINO_ID_BASE}_refresh"
            )

        # 3. シリアライズして返却
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # 登録 (POST /api/t-artists/)
    # ------------------------------------------------------------------
    @logging_process_with_sql(f"{KINO_ID_BASE}_create")
    def create(self, request, *args, **kwargs):
        return self._execute_action(self._perform_create, request, *args, **kwargs)

    def _perform_create(self, request):
        """Serviceを使用して登録処理を実行"""
        # 1. 専用のCreateSerializerでバリデーション
        serializer = Model_T_ArtistCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 2. Service実行
        artist_instance = self.artist_service.create_artist(
            user_profile=request.user.user_t_profile_set,
            validated_data=serializer.validated_data,
            kino_id=f"{KINO_ID_BASE}_create",
        )

        # 3. レスポンス用Serializerで返却
        res_serializer = self.get_serializer(artist_instance)
        return Response(res_serializer.data, status=status.HTTP_201_CREATED)

    # ------------------------------------------------------------------
    # 更新 (PUT/PATCH /api/t-artists/{id}/)
    # ------------------------------------------------------------------
    @logging_process_with_sql(f"{KINO_ID_BASE}_update")
    def update(self, request, *args, **kwargs):
        # partial_update(PATCH) の場合もここを通る
        return self._execute_action(super().update, request, *args, **kwargs)

    # ------------------------------------------------------------------
    # 削除 (DELETE /api/t-artists/{id}/)
    # ------------------------------------------------------------------
    @logging_process_with_sql(f"{KINO_ID_BASE}_delete")
    def destroy(self, request, *args, **kwargs):
        return self._execute_action(super().destroy, request, *args, **kwargs)

    # ------------------------------------------------------------------
    # Spotifyアーティスト検索 (GET /api/t-artists/search_spotify/?q=アーティスト名)
    # ------------------------------------------------------------------
    @logging_process_with_sql(f"{KINO_ID_BASE}_search_spotify")
    @action(detail=False, methods=["get"], url_path="search-spotify")
    def search_spotify(self, request, *args, **kwargs):
        """
        Spotify APIからアーティストを検索する（DB未登録のものを含む）
        """
        return self._execute_action(
            self._perform_search_spotify, request, *args, **kwargs
        )

    def _perform_search_spotify(self, request, *args, **kwargs):
        # 1. クエリパラメータ 'q' (検索ワード) の取得
        query = request.query_params.get("q")
        if not query:
            return Response(
                {"detail": "検索キーワード(q)を指定してください。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2. SpotifyService を使って検索実行
        # 既に共通の SpotifyService に search_artists がある想定
        search_results = self.artist_service.spotify_service.search_artists(
            query=query, limit=20
        )

        # 3. 検索結果の加工
        # フロントエンドが使いやすいように、Spotifyの生データを整形して返す
        # ※ ここで「既に自社DBに登録済みか」のフラグを立ててあげると親切です
        spotify_ids_in_results = [item["id"] for item in search_results]
        registered_ids = T_Artist.objects.filter(
            user=request.user.user_t_profile_set,
            spotify_id__in=spotify_ids_in_results,
            deleted_at__isnull=True,
        ).values_list("spotify_id", flat=True)

        formatted_results = []
        for item in search_results:
            formatted_results.append(
                {
                    "spotify_id": item["id"],
                    "name": item["name"],
                    "image_url": item["images"][0]["url"] if item["images"] else None,
                    "genres": item.get("genres", []),
                    "popularity": item.get("popularity"),
                    "is_registered": item["id"] in registered_ids,  # 登録済みチェック
                }
            )

        return Response(formatted_results, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # 共通実行メソッド
    # ------------------------------------------------------------------
    def _execute_action(self, action_func, request, *args, **kwargs):
        kino_id = f"{KINO_ID_BASE}_{self.action}"

        log_output_by_msg_id(
            log_id="MSGI003",
            params=[
                kino_id,
                str(request.query_params if request.method == "GET" else request.data),
            ],
            logger_name=LOG_METHOD.APPLICATION.value,
        )

        try:
            response = action_func(request, *args, **kwargs)

            log_output_by_msg_id(
                log_id="MSGI004",
                params=[kino_id, str(response.data)],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            return response

        except (ApplicationError, APIException, Http404):
            # これらはDRFやカスタムハンドラが適切なコード(404, 403等)を返すべきものなので
            # そのまま親へスローする
            raise
        except Exception as e:
            raise ApplicationError() from e

    def perform_destroy(self, instance: T_Artist):
        """論理削除"""
        instance.updated_by_id = self.request.user.id
        instance.updated_method = f"{KINO_ID_BASE}_delete"
        instance.deleted_at = timezone.now()
        instance.save()
