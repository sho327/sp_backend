from rest_framework import serializers

class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    パスワードリセット実行APIのSerializerクラス
    """
    raw_token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
