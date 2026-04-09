from rest_framework import serializers

class AccountActivateSerializer(serializers.Serializer):
    """
    アカウントアクティベートAPIのSerializerクラス
    Create 
        Author: Kato Shogo
    """

    token = serializers.CharField(required=True)
