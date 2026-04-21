import json
from django.contrib import admin
from datetime import timedelta
from django.utils import timezone
from unfold.components import BaseComponent, register_component

from apps.account.models import T_LoginHistory

admin.site.index_title = "SpotifyMixer"

@register_component
class LoginTrendChart(BaseComponent):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        labels = []
        data = []
        today = timezone.now().date()
        
        for i in range(6, -1, -1):
            target_date = today - timedelta(days=i)
            labels.append(target_date.strftime("%m/%d"))
            # その日の全ログイン試行回数
            count = T_LoginHistory.objects.filter(created_at__date=target_date).count()
            data.append(count)

        context.update({
            "height": 240,
            "data": json.dumps({
                "labels": labels,
                "datasets": [{
                    "label": "ログイン試行回数",
                    "data": data,
                    "borderColor": "var(--color-primary-600)", # 線の色
                    "backgroundColor": "transparent",           # 背景は透明に
                    "tension": 0.4,                             # 線を滑らかにする
                }]
            }),
            # 軸の最小値を0に固定し、不要な余白を減らすオプション
            "options": json.dumps({
                "scales": {
                    "y": {
                        "beginAtZero": True,
                        "ticks": {"stepSize": 1} # 1単位でメモリを表示
                    }
                },
                "maintainAspectRatio": False
            })
        })
        return context