from rest_framework import serializers

class PasswordResetSerializer(serializers.Serializer):
    """
    パスワードリセットAPIのSerializerクラス
    """
    email = serializers.EmailField(required=True)
