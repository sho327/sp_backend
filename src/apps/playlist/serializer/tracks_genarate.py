from rest_framework import serializers

class ArtistInputSerializer(serializers.Serializer):
    """
    アーティスト単位の情報を保持するSerializer
    setlistfm_mbidはここではあえて必須にせず、バリデーションは親Serializerに任せる
    """
    deezer_id = serializers.CharField()
    # --------------------------------------
    # 直近のセトリを絞る際に必要
    # --------------------------------------
    # SpotifyAPIへ直近のセトリの曲名/アーティスト名称で検索する際に利用
    name = serializers.CharField(required=False)
    # ※こちらは未設定も許可する/未設定の場合は、サービス側で「MusicBrainz」より最新のMBIDの取得を行った上で直近のセトリ取得を実行
    mbid = serializers.CharField(required=False, allow_null=True, allow_blank=True)

class TracksGenerateRequestSerializer(serializers.Serializer):
    """
    入力：フロントエンドから送られてくるデータの検品
    """

    # リストを個別に分けるのではなく、オブジェクトのリストとして受け取る
    artists = serializers.ListField(
        child=ArtistInputSerializer(),
        required=True,
        allow_empty=False,
    )
    pattern = serializers.ChoiceField(
        choices=["top_tracks", "set_list"],
        required=True,
    )
    get_tracks_count = serializers.IntegerField(
        min_value=1,
        max_value=20,
        default=5,
    )
    related_artists_count = serializers.IntegerField(
        min_value=0,
        max_value=5,
        default=0,
    )

    def validate(self, data):
        pattern = data.get("pattern")
        artists = data.get("artists", [])
        # set_listの時だけアーティスト名の必須チェック、MBID取得判定フラグを付与する
        if pattern == "set_list":
            errors = {}
            for index, artist in enumerate(artists):
                # 名前が存在しない、または空文字の場合
                if not artist.get("name"):
                    errors[index] = {"name": ["set_list生成時にはこのフィールドが必須です"]}
                # mbidが無い場合、Trueになる
                artist["need_mbid_fetch"] = not bool(artist.get("setlistfm_mbid"))
            if errors:
                # バリデーションエラーを投げる
                raise serializers.ValidationError({"artists": errors})
        
        return data

