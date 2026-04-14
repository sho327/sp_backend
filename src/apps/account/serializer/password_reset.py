from rest_framework import serializers

class PasswordResetRequestSerializer(serializers.Serializer):
    """
    入力：フロントエンドから送られてくるデータの検品
    """
    email = serializers.EmailField(
        required=True, 
        help_text="リセットメール送信先のアドレス"
    )

class PasswordResetResponseSerializer(serializers.Serializer):
    """
    出力：フロントエンドへ返すデータの定義
    """
    pass
