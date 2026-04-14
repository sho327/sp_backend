from rest_framework import serializers

class LoginRequestSerializer(serializers.Serializer):
    """
    入力：フロントエンドから送られてくるデータの検品
    """
    email = serializers.EmailField(required=True, help_text="メールアドレス")
    password = serializers.CharField(required=True, help_text="パスワード")

class LoginResponseSerializer(serializers.Serializer):
    """
    出力：フロントエンドへ返すデータの定義
    ※ refresh_token は Cookie 管理のため、ここには含めない
    """
    access_token = serializers.CharField(help_text="アクセストークン(JWT等)")
