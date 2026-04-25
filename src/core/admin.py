import json
from django.contrib import admin
from datetime import timedelta
from django.utils import timezone
from unfold.components import BaseComponent, register_component

from apps.account.models import T_LoginHistory

@register_component
class LoginTrendChart(BaseComponent):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        labels = []
        total_data = []
        success_data = []
        failure_data = []
        today = timezone.now().date()
        
        # 過去7日分のデータを集計
        for i in range(6, -1, -1):
            target_date = today - timedelta(days=i)
            labels.append(target_date.strftime("%m/%d"))

            # データベースから対象日の全ログインログを1次抽出
            day_queryset = T_LoginHistory.objects.filter(created_at__date=target_date)
            
            # 成功/失敗をそれぞれカウント（is_successfulフラグを利用）
            success_count = day_queryset.filter(is_successful=True).count()
            failure_count = day_queryset.filter(is_successful=False).count()
            
            success_data.append(success_count)
            failure_data.append(failure_count)
            # 成功＋失敗の合計値を計算（折れ線用）
            total_data.append(success_count + failure_count)

        context.update({
            "height": 240,
            "data": json.dumps({
                "labels": labels,
                "datasets": [
                    # --- 【データセット1】合計試行数 (点線の折れ線) ---
                    {
                        "type": "line",                # 混合グラフにするため明示的にlineを指定
                        "label": "合計試行数",
                        "data": total_data,
                        "borderColor": "#64748b",      # Slate 500: 目立ちすぎない落ち着いたグレー
                        "borderDash": [5, 5],          # 点線の設定: 5px描画して5px空ける
                        "borderWidth": 2,              # 線の太さ
                        "pointRadius": 4,              # プロット点のサイズ（クリックやホバーをしやすくする）
                        "pointBackgroundColor": "#64748b",
                        "backgroundColor": "transparent", # 線の下を塗りつぶさない
                        "tension": 0.3,                # 0.4より少し抑えて、データの変化をシャープに見せる
                        "order": 1                     # 描画の重なり順: 1にすることで棒グラフの手前に表示
                    },
                    # --- 【データセット2】成功数 (緑の棒) ---
                    {
                        "type": "bar",
                        "label": "成功",
                        "data": success_data,
                        "backgroundColor": "#10b981",  # Emerald 500: ポジティブな緑
                        "borderRadius": 2,             # 棒の角をわずかに丸くする（モダンな印象に）
                        "order": 2                     # 折れ線の後ろ側に描画
                    },
                    # --- 【データセット3】失敗数 (赤の棒) ---
                    {
                        "type": "bar",
                        "label": "失敗",
                        "data": failure_data,
                        "backgroundColor": "#ef4444",  # Red 500: 警告を意味する赤
                        "borderRadius": 2,             # 角丸
                        "order": 2                     # 折れ線の後ろ側に描画
                    }
                ]
            }),
            "options": json.dumps({
                "scales": {
                    "x": {
                        # stacked: False により、成功と失敗を「積み上げ」ず「並列」にする
                        # 失敗が成功の下に隠れるのを防ぎ、赤い棒を常に見えるようにする
                        "stacked": False,
                    },
                    "y": {
                        "beginAtZero": True,           # 最小値を必ず0にする
                        "ticks": {"stepSize": 1}       # 1件刻みの整数でメモリを表示
                    }
                },
                "plugins": {
                    "legend": {
                        "display": True,               # 各色のラベル（凡例）を表示
                        "position": "bottom"           # グラフの下側に配置
                    },
                    "tooltip": {
                        # マウスを合わせた時、同じ日付(index)のデータをまとめてツールチップに出す
                        "mode": "index",
                        "intersect": False             # 線や棒にピッタリ合わせなくても表示されるようにする
                    }
                },
                "maintainAspectRatio": False          # 親要素の高さ(height: 240)に合わせて伸縮させる
            })
        })
        return context