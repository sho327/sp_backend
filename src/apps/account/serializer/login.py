from rest_framework import serializers

class LoginSerializer(serializers.Serializer):
    """
    ログインAPIのSerializerクラス
    Create
        Author: Kato Shogo
    """

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)
