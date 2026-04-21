from rest_framework import serializers

class SignupRequestSerializer(serializers.Serializer):
    """
    入力：フロントエンドから送られてくるデータの検品
    """
    email = serializers.EmailField(
        required=True, 
        help_text="メールアドレス"
    )
    password = serializers.CharField(
        required=True, 
        write_only=True, 
        style={'input_type': 'password'},
        # min_length=8,
        help_text="パスワード"
    )

class SignupResponseSerializer(serializers.Serializer):
    """
    出力：フロントエンドへ返すデータの定義
    """
    pass
