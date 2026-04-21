import os
import uuid
from pathlib import Path
from typing import BinaryIO, Optional
from django.conf import settings

# --- コアモジュール ---
from core.consts import LOG_METHOD
from core.utils.log_helpers import log_output_by_msg_id
from core.exceptions.exceptions import ExternalServiceError


class StorageService:
    def __init__(self):
        # settings.py の MEDIA_ROOT を使用する
        self.base_path = Path(settings.MEDIA_ROOT)
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
            
            # デバッグログ出力
            log_output_by_msg_id(
                log_id="MSGD001",
                params=[f"DEBUG: ファイルがアップロードされます。 保存先パス: {file_path.absolute()}"],
                logger_name=LOG_METHOD.APPLICATION.value,
            )

            # 保存
            with open(file_path, "wb") as f:
                # file_dataがInMemoryUploadedFileの場合はread()で取得
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
            # 1. URLパス(相対パス)から Path オブジェクトを作成
            # 念のため '/' を取り除く
            relative_path = Path(file_url.lstrip("/"))
            
            # 2. base_path を結合して絶対パス(または正しい相対パス)を生成
            file_path = self.base_path / relative_path

            # デバッグログ出力
            log_output_by_msg_id(
                log_id="MSGD001",
                params=[f"DEBUG: ファイルが削除されます。 削除対象パス: {file_path.absolute()}"],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            
            if file_path.exists():
                os.remove(file_path)
                return True
            
            # デバッグログ出力
            log_output_by_msg_id(
                log_id="MSGW001",
                params=[f"削除対象ファイルが存在しませんでした。(ファイルを削除せず処理は続行されます。) 削除対象パス: {file_path.absolute()}"],
                logger_name=LOG_METHOD.APPLICATION.value,
            )
            return False
        except Exception as e:
            print(f"File Deletion Failed: {e}")
            return False