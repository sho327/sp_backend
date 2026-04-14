from rest_framework import serializers
from apps.common.models import T_FileResource

class FileResourceBaseSerializer(serializers.ModelSerializer):
    """ベース定義"""
    class Meta:
        model = T_FileResource
        fields = '__all__'

class FileResourceMiniResponseSerializer(FileResourceBaseSerializer):
    """
    【最小構成】
    画像URLだけを返す。
    リスト表示や、アーティストのプロフィールの簡易表示に使用。
    """
    # urlはプロパティなので明示的に指定し、一緒に返されるように設定
    url = serializers.ReadOnlyField()

    class Meta(FileResourceBaseSerializer.Meta):
        # 外部URLか内部ファイルかを隠蔽して'url'だけを返す
        fields = ['id', 'url']

class FileResourceFullResponseSerializer(FileResourceBaseSerializer):
    """
    【最大構成】
    ファイル名、サイズ、種別など全ての情報を返す。
    管理画面や、ファイル詳細情報を表示する画面に使用。
    """
    # urlはプロパティなので明示的に指定し、一緒に返されるように設定
    url = serializers.ReadOnlyField()

    class Meta(FileResourceBaseSerializer.Meta):
        # モデルの全カラム + 追加した url を指定(__all__だとプロパティであるurlが入らない)
        fields = [f.name for f in T_FileResource._meta.fields] + ['url']
