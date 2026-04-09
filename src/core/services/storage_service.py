from typing import BinaryIO, Optional

from core.exceptions import ExternalServiceError

# 役割: Cloudinary/S3など、外部ストレージへのファイルアップロード・削除処理を統一的に扱う。
# 利用例: ユーザーのアバター画像、作品のサムネイル画像の保存/削除。


class StorageService:
    """
    外部ストレージ（Cloudinary/S3など）へのファイルアップロード・削除処理を一括管理するサービス。
    外部通信の責務をビジネスロジックから分離する。
    """

    def __init__(self):
        pass

    def upload_file(
        self, file_data: BinaryIO, folder_path: str, filename: str
    ) -> Optional[str]:
        """
        ファイルを外部ストレージにアップロードし、公開URLを返す。

        Args:
            file_data: アップロードするファイルデータ
            folder_path: 保存先フォルダパス
            filename: ファイル名

        Returns:
            アップロードされたファイルの公開URL

        Raises:
            ExternalServiceError: アップロードに失敗した場合
        """
        try:
            # --- [TODO] Cloudinary SDKなどを使ったアップロード処理を実装 ---
            # 例:
            # import cloudinary.uploader
            # result = cloudinary.uploader.upload(file_data, folder=folder_path, public_id=filename)
            # return result['secure_url']

            # 暫定実装（開発環境用）
            print(f"File uploaded to: {folder_path}/{filename}")
            # 成功時はURLを返す
            return f"https://cdn.shelio.com/{folder_path}/{filename}.png"

        except Exception as e:
            # 外部サービスのエラーとして例外を投げる
            raise ExternalServiceError(
                message="ファイルのアップロードに失敗しました。",
                details={
                    "folder_path": folder_path,
                    "filename": filename,
                    "internal_error": str(e),
                },
            )

    def delete_file(self, file_url: str) -> bool:
        """
        公開URLに基づいてファイルを外部ストレージから削除する。

        Args:
            file_url: 削除するファイルの公開URL

        Returns:
            削除に成功した場合True、失敗した場合False

        Raises:
            ExternalServiceError: 削除に失敗した場合（オプション）
        """
        try:
            # --- [TODO] 外部ストレージの削除処理を実装 ---
            # 例:
            # import cloudinary.uploader
            # cloudinary.uploader.destroy(public_id)

            # 暫定実装（開発環境用）
            print(f"File deleted: {file_url}")
            return True
        except Exception as e:
            # ログ出力は呼び出し側で行うため、ここでは例外を投げるかFalseを返す
            print(f"Storage Deletion Failed: {e}")
            return False
