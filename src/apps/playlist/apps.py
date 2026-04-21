from django.apps import AppConfig


class PlaylistConfig(AppConfig):
    # アプリケーションの完全なドット区切りパス(例: プロジェクト名が「config」だった場合、「config.[name]」)
    name = "apps.playlist"
    # 管理画面での表示名など(任意)
    verbose_name = "プレイリスト機能"
    # データベースのスケーラビリティを確保するため、BigAutoFieldを明示的に指定
    default_auto_field = "django.db.models.BigAutoField"