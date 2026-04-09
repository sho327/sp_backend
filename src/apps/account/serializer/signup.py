from rest_framework import serializers

class SignupSerializer(serializers.Serializer):
    """
    新規登録APIのSerializerクラス
    Create 
        Author: Kato Shogo
    """

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)
