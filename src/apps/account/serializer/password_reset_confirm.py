from rest_framework import serializers

class PasswordResetConfirmRequestSerializer(serializers.Serializer):
    """
    入力：フロントエンドから送られてくるデータの検品
    """
    raw_token = serializers.CharField(
        required=True, 
        help_text="パスワードリセット用トークン"
    )
    new_password = serializers.CharField(
        required=True, 
        write_only=True, 
        style={'input_type': 'password'},
        min_length=8,
        help_text="新しいパスワード"
    )

class PasswordResetConfirmResponseSerializer(serializers.Serializer):
    """
    出力：フロントエンドへ返すデータの定義
    """
    pass
