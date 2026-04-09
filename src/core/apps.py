from django.apps import AppConfig


class CoreConfig(AppConfig):
    # アプリケーションの完全なドット区切りパス
    # プロジェクト名が 'config' だった場合: 'config.[name]'
    name = "core"
    # 管理画面での表示名など（任意）
    verbose_name = "コア機能"
    # データベースのスケーラビリティを確保するため、BigAutoFieldを明示的に指定
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        # アプリケーション起動時にバリデーションを実行
        from core.validators.validate_required_settings import (
            validate_required_settings,
        )

        validate_required_settings()
