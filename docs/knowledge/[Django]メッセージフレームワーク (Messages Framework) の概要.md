## Django メッセージフレームワーク(Messages Framework)の概要

Djangoのメッセージフレームワーク（`django.contrib.messages`）は、**リクエストをまたいで**ユーザーに一時的な通知（成功、警告、エラーなど）を伝えるための仕組みです。

これは、処理後にページをリダイレクト（`redirect()`）する場合など、次のHTTPリクエストでユーザーにフィードバックを表示したいときに不可欠な機能です。

-----

## メッセージフレームワークの使い方

メッセージフレームワークの利用は、主に**ビューでのメッセージの追加**と**テンプレートでの表示**の2ステップで行います。

### 1\. ビュー（Pythonコード）でのメッセージの追加

ビュー関数またはクラス内で、`django.contrib.messages` をインポートし、リクエストオブジェクトを使ってメッセージを追加します。メッセージは自動的にセッションに保存されます。

  * **インポート:** `from django.contrib import messages`
  * **構文:** `messages.レベル(request, 'メッセージ内容')`

| 関数 (レベル) | 用途 | メッセージタグ |
| :--- | :--- | :--- |
| `messages.debug()` | 開発者向けのデバッグ情報 | `debug` |
| `messages.info()` | 一般的な通知 | `info` |
| `messages.success()` | **成功**時のフィードバック | `success` |
| `messages.warning()` | **警告**や注意喚起 | `warning` |
| `messages.error()` | **致命的なエラー** | `error` |

```python
from django.contrib import messages
from django.shortcuts import redirect, render

def password_reset_request_view(request):
    if request.method == 'POST':
        # ... 認証サービスの処理 ...
        try:
            # 処理成功（列挙攻撃対策のため、ユーザー有無にかかわらず）
            messages.info(request, "パスワード再設定用のメールを送信しました。")
            return redirect('account:password_reset_pending')
        
        except Exception:
            # 予期せぬエラー
            messages.error(request, "システムエラーが発生しました。時間をおいて再試行してください。")
            return redirect('account:login') # 安全な場所にリダイレクト
    
    return render(request, 'password_reset_request.html')
```

-----

### 2\. テンプレート（HTML）でのメッセージの表示

メッセージを表示したいすべてのテンプレート（通常は `base.html`）に以下のロジックを記述します。

{% raw %}

```html
{% if messages %}
    <div id="messages-container">
        {% for message in messages %}
            {# message.tags には 'success', 'error' などの文字列が含まれます #}
            <div class="alert alert-{{ message.tags }}" role="alert">
                {{ message }}
            </div>
        {% endfor %}
    </div>
{% endif %}
```

{% endraw %}

  * **`{% if messages %}`**: 現在のリクエストにメッセージがキューに入っている場合にのみ、ブロック全体をレンダリングします。
  * **`{{ message.tags }}`**: これを利用することで、CSSフレームワーク（Bootstrap、Tailwind CSS、DaisyUIなど）のクラス名（例: `alert-success` や `text-error`）に直接マッピングでき、メッセージの見た目を変えられます。

-----

## 主な利点

1.  **リダイレクト後の情報伝達:** HTTPリダイレクトは新しいリクエストを開始しますが、メッセージフレームワークはセッションを通じてメッセージを保持し、次のページで確実に表示します。
2.  **一貫したUI/UX:** 全てのメッセージが同じ方法で処理・表示されるため、アプリケーション全体でユーザーフィードバックの一貫性が保たれます。
3.  **メッセージのレベル分け:** 成功、エラー、警告など、メッセージの重要度に応じて異なるスタイルを適用しやすいように設計されています。