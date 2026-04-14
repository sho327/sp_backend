from django.utils import timezone
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response

# --- コアモジュール ---
from core.utils.date_format import date_to_str

class BaseAPIView(APIView):
    def _get_common_meta(self):
        """共通のメタ情報を生成"""
        return {
            "executeAt": date_to_str(timezone.now(), target_format="%Y/%m/%d %H:%M:%S"),
        }

    def get_success_list_response(self, data, count=None, extra_meta=None):
        """
        List（配列）系成功レスポンス
        """
        response_body = self._get_common_meta()
        response_body.update({
            "count": count if count is not None else len(data),
            "results": data  # 必ず 'results' というキーに入れる
        })
        if extra_meta:
            response_body.update(extra_meta)
        return Response(response_body, status=status.HTTP_200_OK)

    def get_success_map_response(self, data, status_code=status.HTTP_200_OK):
        """
        Map（単一オブジェクト）系成功レスポンス
        """
        response_body = self._get_common_meta()
        response_body.update({
            "data": data  # 'results' ではなく 'data' キーに入れる、あるいは直接展開
        })
        return Response(response_body, status=status_code)

# -------------------------------------------------------------------------------------------
# # 使用方法
# -------------------------------------------------------------------------------------------
# 取得のとき（何も指定しない = 200）
# return self.get_success_map_response(serializer.data)
# 登録のとき（201を明示する）
# return self.get_success_map_response(serializer.data, status_code=status.HTTP_201_CREATED)


class CommonResponseMixin:
    """
    ModelViewSet等で共通レスポンス形式を適用するためのMixin
    """
    def get_common_meta(self):
        return {
            "executeAt": date_to_str(timezone.now(), target_format="%Y/%m/%d %H:%M:%S"),
        }

    def finalize_response(self, request, response, *args, **kwargs):
        """
        DRFの標準メソッドをオーバーライド。
        レスポンスが返る直前に、中身を共通の箱に詰め替える。
        """
        # すでにエラー系や特殊な処理で整形済みの場合はそのまま返す
        if not isinstance(response, Response) or response.exception:
            return super().finalize_response(request, response, *args, **kwargs)

        # データの種類（ListかMapか）を判定して詰め替え
        if isinstance(response.data, list):
            # List系
            response.data = {
                **self.get_common_meta(),
                "count": len(response.data),
                "results": response.data
            }
        elif isinstance(response.data, dict):
            # Map系
            # すでに meta 等が入っている場合は二重にラップしないよう配慮
            if "executeAt" not in response.data:
                response.data = {
                    **self.get_common_meta(),
                    "data": response.data
                }

        return super().finalize_response(request, response, *args, **kwargs)

# -------------------------------------------------------------------------------------------
# # 使用方法
# -------------------------------------------------------------------------------------------
# from rest_framework import viewsets
# from core.mixins.response_mixin import CommonResponseMixin

# class ArtistTagViewSet(CommonResponseMixin, viewsets.ModelViewSet):
#     """
#     Mixinを差し込むだけで、
#     GET /tags/ -> { "executeAt": "...", "count": 10, "results": [...] }
#     POST /tags/ -> { "executeAt": "...", "data": {...} }
#     に自動的に変換される。
#     """
#     queryset = M_ArtistTag.objects.filter(deleted_at__isnull=True)
#     serializer_class = ArtistTagSerializer
