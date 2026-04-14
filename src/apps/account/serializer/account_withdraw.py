from rest_framework import serializers

class AccountWithdrawRequestSerializer(serializers.Serializer):
    """
    入力：フロントエンドから送られてくるデータの検品
    ※ 認証済みの request.user.id を使用するため、パラメータ自体は受け取らない。
    """
    pass

class AccountWithdrawResponseSerializer(serializers.Serializer):
    """
    出力：フロントエンドへ返すデータの定義
    """
    pass
