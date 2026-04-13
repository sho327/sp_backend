import os
import uuid
from pathlib import Path
from typing import BinaryIO, Optional

# --- コアモジュール ---
from core.exceptions import ExternalServiceError


class StorageService:
    """
    ストレージサービス
    """

    def __init__(self, base_dir: str = "media"):
        self.base_path = Path(base_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def upload_file(
        self, file_data: BinaryIO, folder_path: str, original_filename: str
    ) -> Optional[str]:
        try:
            # 拡張子の取得 (.png, .jpg など)
            extension = os.path.splitext(original_filename)[1]
            # UUIDで新しいファイル名を生成
            new_filename = f"{uuid.uuid4()}{extension}"

            target_dir = self.base_path / folder_path
            target_dir.mkdir(parents=True, exist_ok=True)
            file_path = target_dir / new_filename

            # 保存
            with open(file_path, "wb") as f:
                # file_data が InMemoryUploadedFile の場合は read() で取得
                f.write(file_data.read())

            # DB保存用のパスを返す
            return f"{folder_path}/{new_filename}"

        except Exception as e:
            raise ExternalServiceError(
                message="ファイルの保存に失敗しました。",
                details={"error": str(e)},
            )

    def delete_file(self, file_url: str) -> bool:
        try:
            # URLパスから実際のファイルパスに変換(先頭の/を取り除く等)
            file_path = Path(file_url.lstrip("/"))
            if file_path.exists():
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"File Deletion Failed: {e}")
            return False
