from rest_framework import serializers
from apps.artist.models import M_ArtistTag

class MasterArtistTagBaseSerializer(serializers.ModelSerializer):
    """
    ベース定義：モデルとの紐付けだけを行う。
    直接は使わず、継承して利用する。
    """
    class Meta:
        model = M_ArtistTag
        fields = '__all__' # 基本は全フィールド対象

class MasterArtistTagMiniResponseSerializer(MasterArtistTagBaseSerializer):
    """
    【最小構成】一覧用
    Metaを上書きして、IDと名称だけに絞り込む
    """
    class Meta(MasterArtistTagBaseSerializer.Meta):
        fields = ['id', 'name']

class MasterArtistTagFullResponseSerializer(MasterArtistTagBaseSerializer):
    """
    【最大構成】詳細用
    Baseの定義（__all__）をそのまま使い、モデルの変更に自動追従させる
    """
    pass
