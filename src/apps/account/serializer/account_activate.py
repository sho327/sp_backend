from rest_framework import serializers

class AccountActivateRequestSerializer(serializers.Serializer):
    """
    入力：フロントエンドから送られてくるデータの検品
    """
    token = serializers.CharField(required=True, help_text="アクティベート用トークン")

class AccountActivateResponseSerializer(serializers.Serializer):
    """
    出力：フロントエンドへ返すデータの定義
    """
    pass
