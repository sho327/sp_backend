from django.conf import settings

"""
SameSite属性をDEBUG定数の状態で設定変更するミドルウェアクラス
Create
    Author: Kato Shogo
"""


class SameSiteMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        for key in response.cookies.keys():
            response.cookies[key]["samesite"] = "Lax" if settings.DEBUG else "None"
            response.cookies[key]["secure"] = not settings.DEBUG
        return response
