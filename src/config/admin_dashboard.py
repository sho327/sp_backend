from django.db.models import Count
from apps.account.models import T_Profile, T_LoginHistory

def dashboard_callback(request, context):
    # 1. ユーザステータスの集計
    status_counts = T_Profile.objects.values('status_code').annotate(count=Count('status_code'))
    stats = {item['status_code']: item['count'] for item in status_counts}
    
    # 2. 初期設定完了率の計算
    total = T_Profile.objects.count()
    completed = T_Profile.objects.filter(is_setup_completed=True).count()
    percent = int((completed / total * 100)) if total > 0 else 0

    # 3. ログイン失敗ログの整形
    failures = T_LoginHistory.objects.filter(is_successful=False).order_by('-created_at')[:10]
    rows = [
        [log.login_identifier, str(log.get_failure_reason_display()), log.created_at.strftime("%Y/%m/%d %H:%M")]
        for log in failures
    ]

    # 4. コンテキスト更新
    context.update({
        "active_users": stats.get(10, 0),
        "locked_users": stats.get(30, 0),
        "frozen_users": stats.get(40, 0),
        "withdrawn_users": stats.get(99, 0),
        
        # プログレスバー用データ
        "setup_completion_percent": percent,
        
        # テーブル用データ
        "table_data": {
            "headers": ["ユーザ識別子", "失敗理由", "日時"],
            "rows": rows
        }
    })
    
    return context