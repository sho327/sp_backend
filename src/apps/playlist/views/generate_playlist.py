from django.db import transaction
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView


class PlaylistCreateView(APIView):
    # Multipart形式(画像/テキスト)を解析できるように設定
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # parser_classes により request.data に画像とテキストが混在して入る
        serializer = PlaylistCreateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        valid_data = serializer.validated_data
        image_file = valid_data["image"]

        # 1. ストレージサービスでリネーム保存
        storage = StorageService()
        stored_path = storage.upload_file(
            file_data=image_file.file,
            folder_path="playlists",
            original_filename=image_file.name,
        )

        try:
            with transaction.atomic():
                # 2. T_Playlist 作成
                playlist = T_Playlist.objects.create(
                    title=valid_data["title"], image_path=stored_path
                )

                # 3. R_PlaylistArtist (中間テーブル) 作成
                # source='artists' を指定している場合、valid_data['artists'] で取得
                relations = [
                    R_PlaylistArtist(playlist=playlist, artist=artist_obj)
                    for artist_obj in valid_data["artists"]
                ]
                R_PlaylistArtist.objects.bulk_create(relations)

            return Response({"status": "success", "id": playlist.id}, status=201)

        except Exception as e:
            # DB保存に失敗した場合は、さっき保存したローカルファイルを削除する後処理
            storage.delete_file(stored_path)
            return Response({"error": "データベースの保存に失敗しました"}, status=500)
